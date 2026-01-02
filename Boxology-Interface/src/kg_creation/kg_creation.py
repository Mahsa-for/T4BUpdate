try:
    from in_memory_rdfizer.generator import kg_generation
except:
    from .in_memory_rdfizer.generator import kg_generation

from SPARQLWrapper import SPARQLWrapper, POST, DIGEST, JSON
import os
import socket

global SPARQL_ENDPOINT , SPARQL_UPDATE_ENDPOINT

def _detect_host(service_name: str = "boxology_kg") -> str:
    env_host = os.getenv("SPARQL_HOST")
    if env_host:
        return env_host
    try:
        socket.gethostbyname(service_name)
        return service_name
    except OSError:
        return "localhost"

_host = _detect_host()
SPARQL_ENDPOINT = f"http://{_host}:8890/sparql"
SPARQL_UPDATE_ENDPOINT = f"http://{_host}:8890/sparql-auth"
print(f"[KG] Using Virtuoso host={_host}")

def _get_query_sparql():
    sparql = SPARQLWrapper(SPARQL_ENDPOINT, defaultGraph=SPARQL_ENDPOINT)
    sparql.setReturnFormat(JSON)
    return sparql


def _get_update_sparql():
    sparql = SPARQLWrapper(SPARQL_UPDATE_ENDPOINT, defaultGraph=SPARQL_ENDPOINT)
    sparql.setReturnFormat(JSON)
    sparql.setMethod(POST)           # <- update MUST be POST
    sparql.setHTTPAuth(DIGEST)
    sparql.setCredentials("dba", "dba")  # or your own user + password
    return sparql

def boxology_exists(source):
	sparql = _get_query_sparql()
	#sparql = SPARQLWrapper(SPARQL_ENDPOINT,defaultGraph=SPARQL_ENDPOINT)
	for boxology in source["boxologies"]:
		boxology_entity = "<http://tool4boxology.org/Boxology/" + boxology["id"] + ">"
		query = "ASK WHERE { " + boxology_entity + " a <http://tool4boxology.org/Boxology> .}"
		sparql.setReturnFormat(JSON)
		sparql.setQuery(query)
		results = sparql.query().convert()
		print(results, "BOXOLOGY EXISTS?")
		if results["boolean"] == True:
			return True
	return False

def insert_triples(triples):
	sparql = _get_update_sparql()
	#sparql = SPARQLWrapper(SPARQL_ENDPOINT,defaultGraph=SPARQL_ENDPOINT)
	query = "INSERT DATA { " + triples + "}"
	sparql.setReturnFormat(JSON)
	sparql.setQuery(query)
	results = sparql.query().convert()

def update_kg(source,triples):
	sparql = _get_update_sparql()
	#sparql = SPARQLWrapper(SPARQL_ENDPOINT,defaultGraph=SPARQL_ENDPOINT)
	for boxology in source["boxologies"]:
		boxology_entity = "<http://tool4boxology.org/Boxology/" + boxology["id"] + ">"
		query = "DELETE WHERE {" 
		query += boxology_entity + " a <http://tool4boxology.org/Boxology> .\n"
		query += boxology_entity + " <http://www.w3.org/2000/01/rdf-schema#label> ?boxology_label .\n"
		query += boxology_entity + " <http://tool4boxology.org/hasPattern> ?design_pattern .\n"
		query += "?design_pattern a <http://tool4boxology.org/DesignPattern> .\n"
		query += "?design_pattern <http://www.w3.org/2000/01/rdf-schema#label> ?pattern_label .\n"
		query += "?design_pattern <http://tool4boxology.org/hasInput> ?input_component .\n"
		query += "?design_pattern <http://tool4boxology.org/hasOutput> ?output_component .\n"
		query += "?design_pattern <http://tool4boxology.org/hasProcess> ?process_component .\n"
		query += "?input_component a <http://tool4boxology.org/Component> .\n"
		query += "?input_component <http://www.w3.org/2000/01/rdf-schema#label> ?input_component_label .\n"
		query += "?input_component <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?input_component_type .\n"
		query += "?process_component a <http://tool4boxology.org/Component> .\n"
		query += "?process_component <http://www.w3.org/2000/01/rdf-schema#label> ?process_component_label .\n"
		query += "?process_component <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?process_component_type .\n"
		query += "?output_component a <http://tool4boxology.org/Component> .\n"
		query += "?output_component <http://www.w3.org/2000/01/rdf-schema#label> ?output_component_label .\n"
		query += "?output_component <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?output_component_type .\n"
		query += "?input_component <http://tool4boxology.org/inputRoleParticipatesInProcess> ?process_component .\n"
		query += "?process_component <http://tool4boxology.org/outputRoleParticipatesInProcess> ?output_component .\n"
		query += "}"
		sparql.setReturnFormat(JSON)
		sparql.setQuery(query)
		results = sparql.query().convert()
	insert_triples(triples)

def create_kg(source):
	knowledge_graph = kg_generation(source)
	update_needed = boxology_exists(source)
	if update_needed:
		update_kg(source,knowledge_graph)
	else:
		insert_triples(knowledge_graph)

