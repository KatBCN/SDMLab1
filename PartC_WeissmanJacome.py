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
    query = '''CALL gds.louvain.stream("Author_Similarity_Graph_Papers",
               {nodeLabels:['Author'], relationshipTypes:['Similar'], 
               relationshipWeightProperty:'score'})
               YIELD nodeId, communityId
               RETURN gds.util.asNode(nodeId).name as author, communityId
               ORDER BY communityId '''
    louvain_results = graph.run(query).to_data_frame()
    print(louvain_results)
    print(louvain_results.value_counts('communityId'))


#run all calls
# create_graph_instance()
# run_node_similarity()
run_louvain()

