import py2neo

graph = py2neo.Graph("bolt://localhost:7687", user='neo4j', password='1234katmat')


def get_keywords():
    # Manually define the set of keywords of each community.
    # Implemented as a list of lists instead of a dictionary
    # for easier Cypher management
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


def define_communities():
    # Manually define the available communities.
    communities = ['Databases', 'AI', 'Supercomputing']

    return communities


def load_communities():
    # Load communities into the DB
    communities = define_communities()

    for comm in communities:
        graph.run('MERGE (n:Community {{name: \'{}\'}}) '.format(comm))


def get_communities():
    # Get communities from the DB
    ask_query = '''MATCH (c:Community) RETURN c.name'''
    communities = list(graph.run(ask_query).to_series())

    return communities


def assign_community_keywords():
    # Assign to each community it's set of keywords.
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


def link_communities():
    # create relations between journals/congresses and their communities when at least 90% of their papers
    # are associated to that communities' keywords.
    query = '''MATCH (co:Community)-[:STUDIES]-(keyword) 
               WITH apoc.map.fromLists([co.name], [collect(keyword.topic)]) AS community_kws 
               MATCH (kw:Keyword)-[]-(p:Paper)-[]-(edition)-[]-(jc) 
               WHERE (jc:Conference or jc:Journal) AND (edition:JournalVolume OR edition:conferenceEdition) 
               UNWIND keys(community_kws) AS comm 
               WITH comm, jc, ID(p) AS paper, kw.topic AS keyword, 
               CASE  
                   WHEN kw.topic in community_kws[comm] THEN true ELSE null  
                   END as related 
               WITH jc, comm, paper, CASE  
               WHEN any(x in collect(related) WHERE x IS NOT null) THEN 1 ELSE 0 END AS rel_papers  
               WITH jc, comm, avg(rel_papers) AS rel_score 
               MATCH (jc), (community:Community {name: comm}) 
               WHERE rel_score >= 0.9 
               MERGE (jc)-[rel:IS_PART_OF]->(community)  
               SET rel.rel_score = rel_score'''
    graph.run(query)

    print('Journals/Congresses assigned to their communities.')


def create_graph_instances_D():
    communities = get_communities()

    # Creates a graph projection and stores it in the graph catalog
    for comm in communities:
        creation_query = '''CALL gds.graph.create.cypher(
                            '{comm}_Papers',
                            'MATCH (comm:Community)<-[:IS_PART_OF]-()<-[:EDITION_OF|VOLUME_OF]-()<-[:PUBLISHED_IN]-(p:Paper) 
                             WHERE comm.name = "{comm}" RETURN id(p) AS id, labels(p) AS labels',
                            'MATCH (p1)-[r:CITES]->(p2) RETURN id(p1) AS source, id(p2) AS target, type(r) AS type',
                            {{validateRelationships: false}})
                             YIELD graphName AS graph, nodeQuery, nodeCount AS nodes, relationshipCount AS rels'''
        creation_query = creation_query.format(comm=comm)

        graph.run(creation_query)


def run_pageRank():
    # get communities
    communities = get_communities()

    for comm in communities:
        # Runs the pageRank algorithm over communities' sub-graphs and
        # modifies the database to add the 'score' and 'top100' properties
        # to papers in the top 100 of the pageRank score of a Community
        query = '''CALL gds.pageRank.stream('{comm}_Papers') 
                   YIELD nodeId, score
                   WITH nodeId, score
                   ORDER BY score DESC, nodeId ASC LIMIT 100
                   MATCH (p:Paper) WHERE ID(p) = nodeId 
                   SET p.{comm}_top100 = true 
                   RETURN p.title, p.top100'''.format(comm=comm)
        result = graph.run(query).to_data_frame()
        print(comm, '\n', result)


def recommend_reviewers(community):
    query = '''MATCH (a:Author)-[:WROTE]->(p:Paper {{{comm}_top100: true}}) 
               RETURN a.name as author, 
               CASE WHEN count(*) >= 2 THEN true ELSE false END AS guru
               ORDER BY guru DESC'''
    query = query.format(comm=community)
    result = graph.run(query).to_data_frame()
    print(community, '\n', result)


### Run statements
load_communities()
assign_community_keywords()
link_communities()

create_graph_instances_D()
run_pageRank()

recommend_reviewers('Databases')

