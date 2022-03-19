import numpy as np
import py2neo
import random

graph = py2neo.Graph("bolt://localhost:7687", user='neo4j', password='1234katmat')


def load_journals(filename):
    with open('Cypher queries/CYPHER_journals_creation.txt', 'r') as queryfile:
        query = queryfile.read().format(filename)
        graph.run(query)
        print('Loaded {} into the DB!'.format(filename))


def load_conferences(filename):
    with open('Cypher queries/CYPHER_conferences_creation.txt', 'r') as queryfile:
        query = queryfile.read().format(filename)
        graph.run(query)
        print('Loaded {} into the DB!'.format(filename))


def create_corresponding_authors(filename):
    with open('Cypher queries/CYPHER_corresponding_authors.txt', 'r') as queryfile:
        query = queryfile.read().format(filename)
        graph.run(query)
        print('Loaded {}\'s corr. auth. into the DB!'.format(filename))


journals = ['BigDataMiningAndAnalytics',
            'IEEETransactionsOnBigData',
            'DataIntelligence']
conferences = ['IEEE_ACM_BDCAT',
               'IEEE_BigComp']


for journal in journals:
    load_journals(journal)

for conf in conferences:
    load_conferences(conf)

for element in journals + conferences:
    create_corresponding_authors(element)


def random_keywords():
    n = np.random.randint(1, 3)

    keywords = ['Data Management', 'Indexing', 'Data Modeling', 'Big Data',
                'Data Processing', 'Data Storage', 'Data Querying']

    assign_list = random.sample(keywords, n)
    return assign_list


def load_keywords():
    keywords = ['Data Management', 'Indexing', 'Data Modeling', 'Big Data',
                'Data Processing', 'Data Storage', 'Data Querying']
    for kw in keywords:
        graph.run('CREATE (n:Keyword {{topic: \'{}\'}}) '.format(kw))


def assign_keywords():
    paper_ids = graph.run('match (n:Paper) return ID(n) as id').to_data_frame()['id']

    for paper_id in paper_ids:
        keywords = random_keywords()
        for kw in keywords:
            graph.run('MATCH (p:Paper), (k:Keyword) WHERE ID(p) = {paper_id}'
                      ' AND k.topic = \'{kw}\' MERGE (p)-[:DISCUSSES]->(k)'.format(paper_id=paper_id,
                                                                              kw=kw))


load_keywords()
assign_keywords()


