import numpy as np
import py2neo
import random


graph = py2neo.Graph("bolt://localhost:7687", user='neo4j', password='1234katmat')

random.seed(42)
np.random.seed(42)


def get_keywords():
    db_keywords = ['Data Management', 'Indexing', 'Data Modeling', 'Big Data',
                'Data Processing', 'Data Storage', 'Data Querying']
    ai_keywords = ['Deep Learning', 'Machine Learning','Reinforcement',
                   'Neural Networks', 'Natural Language Processing',
                   'Artificial Intelligence', 'Bayesian Regression']
    sc_keywords = ['High-Performance Computing', 'Supercomputing',
                   'Parallelization','Quantum Computing', 'Cooling',
                   'Chip Architecture', 'GPU Supercomputing']
    keywords = [db_keywords, ai_keywords, sc_keywords]
    return keywords


def get_communities():
    communities = ['Databases', 'AI', 'Supercomputing']

    return communities


def load_communities():
    communities = get_communities()

    for comm in communities:
        graph.run('MERGE (n:Community {{name: \'{}\'}}) '.format(comm))


def assign_community_keywords():
    kw_sets = get_keywords()
    communities = get_communities()

    community_kw_dict = dict(zip(communities, kw_sets))

    for comm in community_kw_dict.keys():
        for kw in community_kw_dict[comm]:
            query = 'MATCH (c:Community), (k:Keyword) WHERE c.name = "{comm}" ' \
                    'AND k.topic = "{kw}" MERGE (c)-[:STUDIES]->(k)'
            query = query.format(comm=comm, kw=kw)

            graph.run(query)

    print('Community keywords assigned.')


def link_communities():  #### MIGHT LOOK INTO UNWINDING PAPERS, now disjoint
    #create relations between journals/congresses and their communities
    query = '''match (co:Community)-[:STUDIES]-(keyword) with apoc.map.fromLists([co.name], [collect(keyword.topic)]) AS community_kws
               match (kw:Keyword)-[]-(p:Paper)-[]-(edition)-[]-(jc) 
               where (jc:Conference or jc:Journal) and (edition:JournalVolume or edition:conferenceEdition)
               unwind keys(community_kws) as comm
               with comm, jc, ID(p) as paper, kw.topic as keyword,
               case 
                   when kw.topic in community_kws[comm] THEN 1
                   ELSE 0 END as rel_papers
               with jc, comm, avg(rel_papers) as rel_score
               match (jc), (community:Community {name: comm})
               where rel_score >= 0.9
               merge (jc)-[rel:IS_PART_OF]->(community)
               set rel.rel_score = rel_score'''
    graph.run(query)

    print('Journals/Congresses assigned to their communities.')


def create_graph_instance_D():
    ###### TO DO
    ###BUILD CYPHER QUERY TO CREATE SUBGRAPHS OF COMMUNITY--->PAPERS FOR EACH COMMUNITY
    ###THEN BUILD A FUNCTION TO RUN PAGERANK OVER ALL OF THEM INDIVIDUALLY, GET TOP 100
    ###THEN BUILD A FUNCTION TO GET THE AUTHORS OF THOSE PAPERS + THE GURUS OF THE COMM

    #Get journal/conferences
    ask_query = '''MATCH (p:Paper)-[:PUBLISHED_IN]-()-[]-(jc)-[:IS_PART_OF]->(:Community)
                   WHERE (jc:Conference OR jc:Journal) RETURN jc.title'''
    jourconf = list(graph.run(ask_query).to_series())

    # Creates a graph projection and stores it in the graph catalog
    for jc in jourconf:
        creation_query = '''CALL gds.graph.create('{}', 'Paper', 'CITES')'''.format(jc)
        graph.run(creation_query)


def run_pageRank():
    # Runs the pageRank algorithm over the created database
    query = '''CALL gds.pageRank.stream('myGraph') 
               YIELD nodeId, score
               RETURN gds.util.asNode(nodeId).title AS title, score
               ORDER BY score DESC, title ASC'''
    result = graph.query(query).to_data_frame()
    return result


### Run statements
# load_communities()
# assign_community_keywords()
# link_communities()

create_graph_instance_D()


