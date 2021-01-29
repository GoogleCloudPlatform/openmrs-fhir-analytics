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

See test_spark.ipynb for real examples of how
"""

from typing import List
from datetime import datetime
import pandas
from pyspark.sql import DataFrame
import pyspark.sql.functions as F
import pyspark.sql.types as T


def flatten_obs(obs: DataFrame) -> DataFrame:
  return obs.select(
      obs.subject.patientId.alias('patientId'),
      obs.effective.dateTime.alias('dateTime'),
      obs.value,
      F.explode(obs.code.coding).alias('coding'))


def aggregate_all_codes_per_patient(
    obs: DataFrame,
    codes: List[str]=None,
    start_date: str=None,
    end_date: str=None) -> DataFrame:
  flat_obs = flatten_obs(obs)
  start_obs = flat_obs
  if start_date:
    start_obs = flat_obs.filter(flat_obs.dateTime > start_date)
  date_obs = start_obs
  if end_date:
    date_obs = start_obs.filter(start_obs.dateTime < end_date)
  return date_obs.groupBy([
      flat_obs.patientId,
  ]).pivot('coding.code', values=codes).agg(
      F.count('*').alias('num_obs'),
      F.min(flat_obs.value.quantity.value).alias('min_value'),
      F.max(flat_obs.value.quantity.value).alias('max_value'),
      F.min(flat_obs.dateTime).alias('min_date'),
      F.max(flat_obs.dateTime).alias('max_date')
  )


def join_patients_agg_obs(
    patients: DataFrame,
    agg_obs: DataFrame,
    base_patient_url: str):
  flat_patients = patients.select(
      patients.id, patients.birthDate, patients.gender).withColumn(
      'actual_id', F.regexp_replace('id', base_patient_url, ''))
  return flat_patients.join(
      agg_obs, flat_patients.actual_id == agg_obs.patientId)


def find_age_band(birth_date: str) -> str:
  birth = datetime.fromisoformat(birth_date)
  age = int((datetime.today() - birth).days / 365.25)
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


def agg_buckets(birth_date: str, gender: str) -> List[str]:
  age_band = find_age_band(birth_date)
  return [age_band + '_' + gender, 'ALL-AGES_' + gender,
          age_band + '_ALL-GENDERS', 'ALL-AGES_ALL-GENDERS']


def calc_TX_PVLS(patient_agg_obs: DataFrame, VL_code: str) -> pandas.DataFrame:
  agg_buckets_udf = F.UserDefinedFunction(lambda a, g: agg_buckets(a, g), T.ArrayType(T.StringType()))
  VL_df = patient_agg_obs.withColumn(
      'sup_VL', patient_agg_obs[VL_code + '_max_value'] < 150).withColumn(
      'agg_buckets', agg_buckets_udf(
          patient_agg_obs['birthDate'], patient_agg_obs['gender'])
  )
  num_patients = VL_df.count()
  VL_agg_P = VL_df.select(
      VL_df.sup_VL,
      F.explode(VL_df.agg_buckets).alias('agg_bucket')).groupBy(
      'sup_VL', 'agg_bucket').agg(
      F.count('*').alias('count')).toPandas().sort_values(
      ['agg_bucket', 'sup_VL'])
  VL_agg_P['ratio'] = VL_agg_P['count']/num_patients
  return VL_agg_P
