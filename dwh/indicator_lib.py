# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Set of functions to work with Spark DataFrames containing FHIR resources.

See test_spark.ipynb for real examples of how to create/use these functions.
"""


# TODO move common and query related parts to `query_lib.py` and only keep
#   indicator calculation logic that is independent of Spark here.

from typing import List
from datetime import datetime
from dateutil.parser import parse
import pandas as pd

import common
import query_lib

def _find_age_band(birth_date: str, end_date: datetime) -> str:
  """Given the birth date, finds the age_band for PEPFAR disaggregation."""
  birth = parse(birth_date)
  age = int((end_date - birth).days / 365.25)

  if age < 1:
    return '0-1'
  if age <= 4:
    return '1-4'
  if age <= 9:
    return '5-9'
  if age <= 14:
    return '10-14'
  if age <= 19:
    return '15-19'
  if age <= 24:
    return '20-24'
  if age <= 49:
    return '25-49'
  return '50+'


def _agg_buckets(birth_date: str, gender: str, end_date: datetime) -> List[str]:
  """Generates the list of all PEPFAR disaggregation buckets."""
  age_band = _find_age_band(birth_date, end_date)
  return [age_band + '_' + gender, 'ALL-AGES_' + gender,
          age_band + '_ALL-GENDERS', 'ALL-AGES_ALL-GENDERS']

def _gen_counts_and_ratio(temp_df: pd.DataFrame,  end_date: datetime,
                         ind_name: str) -> pd.DataFrame:
  """Generates aggregated dataframe when supplied with patient-level df"""
  temp_df['buckets'] = temp_df.apply(
    lambda x: _agg_buckets(x.birthDate, x.gender, end_date), axis=1)
  temp_df_exp = temp_df.explode('buckets')
  temp_df_exp = temp_df_exp.groupby(
      [ind_name, 'buckets'], as_index=False).count()[[
      ind_name, 'buckets', 'patientId']].rename(
      columns={'patientId': ind_name + '_count'})
  # calculate ratio
  num_patients = len(temp_df.index)
  temp_df_exp[ind_name + '_ratio'] = temp_df_exp[
                                       ind_name + '_count'] / num_patients
  return temp_df_exp


def calc_TX_PVLS(patient_agg_obs: pd.DataFrame, VL_code: str,
    failure_threshold: int, end_date_str: str = None) -> pd.DataFrame:
  """Calculates TX_PVLS indicator with its corresponding disaggregations.

  Args:
    patient_agg_obs: An output from `patient_query.find_patient_aggregates()`.
    VL_code: The code for viral load values.
    failure_threshold: VL count threshold of failure.
    end_date: The string representation of the last date as 'YYYY-MM-DD'.
  Returns:
    The aggregated DataFrame with age/gender buckets.
  """
  end_date = datetime.today()
  if end_date_str:
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
  temp_df = patient_agg_obs[(patient_agg_obs['code'] == VL_code)].copy()
  # Note the above copy is used to avoid setting a new column on a slice next:
  temp_df['latest_vl_value'] = temp_df['last_value'].astype(float)
  temp_df['sup_VL'] = (temp_df['latest_vl_value'] < failure_threshold)
  temp_df = _gen_counts_and_ratio(temp_df, end_date, 'sup_VL')
  return temp_df


def calc_TX_NEW(patient_agg_obs:  pd.DataFrame, ARV_plan: str,
                start_drug: List[str], end_date_str: str = None) -> pd.DataFrame:
  """Calculates TX_NEW indicator with its corresponding disaggregations.

  TX_NEW indicator counts the number of adults and children newly enrolled
  on antiretroviral therapy (ART) prior to the provided end-date

  Args:
    patient_agg_obs: A DataFrame generated by `patient_query.find_patient_aggregates()`.
    ARV_plan: The concept question code for ANTIRETROVIRAL PLAN
    start_drug: The concept answer codes for START DRUG
    end_date: The string representation of the last date as 'YYYY-MM-DD'.
  Returns:
    The aggregated DataFrame with age/gender buckets.
  """
  end_date = datetime.today()
  if end_date_str:
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
  temp_df = patient_agg_obs[(patient_agg_obs['code'] == ARV_plan)].copy()
  # Note the above copy is used to avoid setting a new column on a slice next:
  temp_df['TX_NEW'] = (temp_df['last_value_code'].isin(start_drug))
  temp_df = _gen_counts_and_ratio(temp_df, end_date, 'TX_NEW')
  return temp_df