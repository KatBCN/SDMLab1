import numpy as np
import py2neo
import random
from bs4 import BeautifulSoup
import requests
import pandas as pd

graph = py2neo.Graph("bolt://localhost:7687", user='neo4j', password='1234katmat')

random.seed(42)
np.random.seed(42)

# adding reviews' content and decision
def upgrade_review_edges():
    papers = list(graph.run('match (n:Paper) return ID(n) as paperid').to_data_frame()['paperid'])

    for paper in papers:
        rev_outcomes = ['true', 'true'] + random.sample(['true', 'false'], 1)

        rev_query = 'MATCH (a:Author)-[r:REVIEWED]->(p:Paper) ' \
                    'WHERE ID(p) = {paper} RETURN ID(r) as reviews'.format(paper=paper)
        reviews = list(graph.run(rev_query).to_data_frame()['reviews'])

        zipped = zip(reviews, rev_outcomes)

        for review, rev_outcomes in zipped:
            query = 'MATCH (:Author)-[rev:REVIEWED]->(p:Paper) ' \
                    'WHERE ID(p) = {paper} AND ID(rev) = {review} ' \
                    'SET rev.content = "some comments", rev.decision = {outcome}'
            query = query.format(paper=paper, review=review, outcome=rev_outcomes)
            graph.run(query)


#adding organizations and affiliations
def get_companies_list():
    # get the response in the form of html
    wikiurl = "https://en.wikipedia.org/wiki/List_of_largest_companies_by_revenue"
    response = requests.get(wikiurl)

    # parse data from the html into a beautifulsoup object
    soup = BeautifulSoup(response.text, 'html.parser')
    wikitable = soup.find('table', {'class': "wikitable"})
    list_object = pd.read_html(str(wikitable))

    # convert list to dataframe
    df = pd.DataFrame(list_object[0])
    df.columns = df.columns.droplevel(0)

    # return companies list
    companies = list(df['Name'])

    return companies


def get_universities_list():
    # get the response in the form of html
    wikiurl = "https://en.wikipedia.org/wiki/QS_World_University_Rankings"
    response = requests.get(wikiurl)

    # parse data from the html into a beautifulsoup object
    soup = BeautifulSoup(response.text, 'html.parser')
    wikitable = soup.find_all('table', {'class': "wikitable"})
    list_object = pd.read_html(str(wikitable))

    # convert list to dataframe
    df = pd.DataFrame(list_object[1])

    # return companies list
    universities = list(df['Institution'])

    return universities


def load_organizations():
    universities = get_universities_list()
    companies = get_companies_list()

    for uni in universities:
        graph.run('CREATE (n:University {{name: "{}"}}) '.format(uni))

    for comp in companies:
        graph.run('CREATE (n:Company {{name: "{}"}}) '.format(comp))


def assign_organizations():
    universities = get_universities_list()
    companies = get_companies_list()

    sampling_pop = universities + universities + universities + companies  # make academic affiliation more common

    author_ids = graph.run('match (n:Author) return ID(n) as id').to_data_frame()['id']

    for author_id in author_ids:
        organization = random.sample(sampling_pop, 1)[0]
        graph.run('MATCH (a:Author), (c) '
                  'WHERE ID(a) = {author_id} AND c.name = "{org}" '
                  'MERGE (a)-[:AFFILIATED_TO]->(c)'.format(author_id=author_id, org=organization))


### run required functions
upgrade_review_edges()
load_organizations()
assign_organizations()
