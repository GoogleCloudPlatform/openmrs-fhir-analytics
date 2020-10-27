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

import java.util.Map;
import java.util.Properties;

import ca.uhn.fhir.parser.IParser;
import io.debezium.data.Envelope.Operation;
import org.apache.camel.Produce;
import org.apache.camel.ProducerTemplate;
import org.apache.camel.RoutesBuilder;
import org.apache.camel.builder.RouteBuilder;
import org.apache.camel.test.junit4.CamelTestSupport;
import org.hl7.fhir.dstu3.model.Encounter;
import org.hl7.fhir.dstu3.model.Resource;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.MockitoJUnitRunner;

@RunWith(MockitoJUnitRunner.class)
public class FhirConverterTest extends CamelTestSupport {
	
	private static final String TEST_ROUTE = "direct:test";
	
	private static final String TEST_RESOURCE = "test FHIR resource";
	
	private static final String TEST_ID = "ID";
	
	@Produce(TEST_ROUTE)
	protected ProducerTemplate eventsProducer;
	
	@Mock
	private OpenmrsUtil openmrsUtil;
	
	@Mock
	private FhirStoreUtil fhirStoreUtil;
	
	@Mock
	private IParser parser;
	
	@Mock
	private Resource resource;
	
	private FhirConverter fhirConverter;
	
	@Override
	protected RoutesBuilder createRouteBuilder() throws Exception {
		return new RouteBuilder() {
			
			@Override
			public void configure() throws Exception {
				
				// set debeziumEventConfigPath
				Properties p = System.getProperties();
				p.put("fhir.debeziumEventConfigPath", "../utils/dbz_event_to_fhir_config.json");
				System.setProperties(p);
				fhirConverter = new FhirConverter(openmrsUtil, fhirStoreUtil, parser);
				
				// Inject FhirUriGenerator;
				from(TEST_ROUTE).process(fhirConverter); // inject target processor here
			}
		};
	}
	
	@Test
	public void shouldFetchFhirResourceAndStore() {
		Map<String, String> messageBody = DebeziumTestUtil.genExpectedBody();
		Map<String, Object> messageHeaders = DebeziumTestUtil.genExpectedHeaders(Operation.UPDATE, "encounter");
		resource = new Encounter();
		resource.setId(TEST_ID);
		Mockito.when(openmrsUtil.fetchFhirResource(Mockito.anyString())).thenReturn(resource);
		Mockito.when(parser.encodeResourceToString(resource)).thenReturn(TEST_RESOURCE);
		
		// Actual event that will tripper process().
		eventsProducer.sendBodyAndHeaders(messageBody, messageHeaders);
		
		Mockito.verify(openmrsUtil).fetchFhirResource(Mockito.anyString());
		Mockito.verify(fhirStoreUtil).uploadResourceToCloud("Encounter", TEST_ID, TEST_RESOURCE);
	}
	
	@Test
	public void shouldIgnoreDeleteEvent() {
		Map<String, String> messageBody = DebeziumTestUtil.genExpectedBody();
		Map<String, Object> messageHeaders = DebeziumTestUtil.genExpectedHeaders(Operation.DELETE, "encounter");
		
		// Actual event that will tripper process().
		eventsProducer.sendBodyAndHeaders(messageBody, messageHeaders);
		
		Mockito.verify(openmrsUtil, Mockito.times(0)).fetchFhirResource(Mockito.anyString());
	}
	
	@Test
	public void shouldIgnoreEventWithNoHeaders() throws Exception {
		Map<String, String> messageBody = DebeziumTestUtil.genExpectedBody();
		
		// Actual event that will tripper process().
		eventsProducer.sendBody(messageBody);
		
		Mockito.verify(openmrsUtil, Mockito.times(0)).fetchFhirResource(Mockito.anyString());
	}
	
	@Test
	public void shouldIgnoreEventWithUnknownTable() throws Exception {
		Map<String, String> messageBody = DebeziumTestUtil.genExpectedBody();
		Map<String, Object> messageHeaders = DebeziumTestUtil.genExpectedHeaders(Operation.UPDATE, "dummy");
		
		// Actual event that will tripper process().
		eventsProducer.sendBodyAndHeaders(messageBody, messageHeaders);
		
		Mockito.verify(openmrsUtil, Mockito.times(0)).fetchFhirResource(Mockito.anyString());
	}
	
}
