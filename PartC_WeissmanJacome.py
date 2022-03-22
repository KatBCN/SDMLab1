import py2neo
import pandas as pd

graph = py2neo.Graph("bolt://localhost:7687", user='neo4j', password='1234katmat')


def create_graph_instance_C():
    # Creates a graph projection and stores it in the graph catalog
    query = '''CALL gds.graph.create('paperCitations', 'Paper', 'CITES')'''
    graph.run(query)


def run_pageRank():
    # Runs the pageRank algorithm over the created database
    query = '''CALL gds.pageRank.stream('myGraph') 
               YIELD nodeId, score
               RETURN gds.util.asNode(nodeId).title AS title, score
               ORDER BY score DESC, title ASC'''
    result = graph.query(query).to_data_frame()
    return result


create_graph_instance_C()
print(run_pageRank())
