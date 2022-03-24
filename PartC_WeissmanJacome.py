import py2neo
import pandas as pd

graph = py2neo.Graph("bolt://localhost:7687", user='neo4j', password='1234katmat')


def create_graph_instance():
    # Creates a graph projection and stores it in the graph catalog
    query = '''CALL gds.graph.create("Author_Similarity_Graph_Papers", ["Author","Paper"],"WROTE");'''
    graph.run(query)


def run_node_similarity():
    # Runs the pageRank algorithm over the created database
    query = '''CALL gds.nodeSimilarity.mutate("Author_Similarity_Graph_Papers", 
                    {mutateRelationshipType:'Similar', mutateProperty:'score',
                    topK:10, similarityCutoff:0.1})'''
    graph.run(query)


def run_louvain():
    query = '''CALL gds.louvain.mutate("Author_Similarity_Graph_Papers",
               {nodeLabels:['Author'], relationshipTypes:['Similar'], 
               relationshipWeightProperty:'score', mutateProperty:'louvainCommunity'});'''
    graph.run(query)


def drop_and_export():
    query1 = '''CALL gds.graph.export('Author_Similarity_Graph_Papers', 
               { dbName: 'AuthorCommunity', additionalNodeProperties: ['name','title']});'''
    query2 = '''CALL gds.graph.drop("Author_Similarity_Graph_Papers");'''

    graph.run(query1)
    graph.run(query2)


#run all calls
create_graph_instance()
run_node_similarity()
run_louvain()
drop_and_export()

