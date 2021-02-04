// Copyright 2020 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package org.openmrs.analytics;

import java.beans.PropertyVetoException;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.Map;

import junit.framework.TestCase;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.junit.MockitoJUnitRunner;
import org.openmrs.analytics.model.EventConfiguration;

@RunWith(MockitoJUnitRunner.class)
public class GetUuidUtilTest extends TestCase {
	
	private JdbcConnectionUtil jdbcConnectionUtil;
	
	private GetUuidUtil getUuidUtil;
	
	private EventConfiguration config;
	
	private Map<String, String> payload = new HashMap<>();;
	
	private final String dbDriver = "com.mysql.cj.jdbc.Driver";
	
	private final String dbUrl = "jdbc:mysql://localhost:3306/openmrs";
	
	private final String dbUser = "root";
	
	private final String dbPassword = "debezium";
	
	private final int dbMaxSize = 50;
	
	private final int dbInitialPoolSize = 10;
	
	private String uuid = "";
	
	@Before
	public void setUp() throws Exception {
		jdbcConnectionUtil = new JdbcConnectionUtil(dbDriver, dbUrl, dbUser, dbPassword, dbMaxSize, dbInitialPoolSize);
		getUuidUtil = new GetUuidUtil(jdbcConnectionUtil);
		config = new EventConfiguration();
		payload.put("name", "patient");
		payload.put("sex", "patient_female");
		payload.put("patient_id", "1");
		config.setParentForeignKey("person_id");
		config.setChildPrimaryKey("patient_id");
		config.setParentTable("person");
	}
	
	@Test
	public void shouldGetUuidFromPatentTbale() throws ClassNotFoundException, PropertyVetoException, SQLException {
		uuid = getUuidUtil.getUuid(config.getParentTable(), config.getParentForeignKey(),
		    payload.get(config.getChildPrimaryKey()));
		assertNotNull(uuid);
		assertEquals(uuid, "1296b0dc-440a-11e6-a65c-00e04c680037");
		
	}
}
