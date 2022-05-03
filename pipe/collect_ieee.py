# Imports
import pandas as pd
import re
from datetime import datetime, timedelta
import time
import json
from os import listdir, path
from os.path import isfile, join

import requests
from bs4 import BeautifulSoup as soup
import lxml
from fake_useragent import UserAgent

# prep for import of own scripts
# # #this only needs to be done because module not in same place as this py
# import sys
# sys.path.insert(0, '.')

# # Importing functions from our own modules
# from utils.collection_utils import datetime_parse

def ieee_searcher(base_url, search_terms, scraped_times0):
      '''
      Collects from IEEE spectrum using search terms
      Only returns first ~4 entries so must be run regularily
      '''
      # Further URL parts
      query_url = 'search/?q='
      C = "&"
      sort_criteria = "order=newest"

      # Lists for saving to
      title_list = []
      url_list = []
      date_list = []

      # Setting up fake user agent to have a proper header
      ua = UserAgent(verify_ssl=False, cache=False)
      user_agent = ua.random
      header = {'User-Agent': user_agent}
      
      for term in search_terms['search_term']:
            
            # Putting together final url
            final_url = base_url + query_url + term + C + sort_criteria
            print(final_url)

            # Making request and saving HTML of request
            # earlier I used .post (instead of.get) 
            # no clear reason why, but comment for the record
            response = requests.get(final_url, headers=header)
            html = soup(response.text, 'lxml')
            
            #Getting all stories
            objects = html.find_all('div',  class_='section_column')#elid=True)#class_= 'clearfix')

            for obj in objects:
                  #going down a level for actual content of interest (possible we would move this to "objects" and skip)
                  items = obj.find_all('div', id='col-right')

                  # Looping through stories to get details
                  for i in items:
                        title_list.append(i.h2.text)
                        url_list.append(i.h2.a['href'])

                        date = i.find('div', class_="social-date")
                        date = date.text.replace('\n', '')
                        date_parsed = datetime.strptime(date, '%d %b %Y')

                        print(date_parsed)
                        date_list.append(date_parsed)

      # Putting lists in Dataframe                        
      collected_df = pd.DataFrame(list(zip(title_list, url_list, date_list)), 
                  columns=['title', 'url', 'date',])      
      
      # List to save text to and preping for dictionary conversion
      relevant_text = []
      relevant_text.append(['title', 'url', 'date', 'text'])

      # Getting last collection time, if none, getting oldest date in results
      try:
            last_collected = datetime.strptime(scraped_times[base_url],'%Y-%m-%dT%H:%M:%SZ')
      except:
            last_collected = min(list(collected_df.date))

      # Looping through Dataframe to get text 
      for index, row in collected_df.iterrows():
            # Only getting text from articles within timedelta = your search frequency
            if row.date > last_collected:
                  print('Fetching: ' + row.url)

                  response = requests.post(row.url) #headers=header)
                  html = soup(response.text, 'lxml')

                  objects = html.find_all('div', id="col-center")
                  article_text = []

                  # Getting all the text from the 'p' tags
                  for obj in objects:
                        paragraph_text = obj.find_all('p')
                        for p in paragraph_text:
                              article_text.append(p.text)
                  article_text = ' '.join(article_text)

                  # Saving that text only if our search term appears in it
                  # In principle for IEEE this is not needed, given the original collection uses search url
                  for word in search_terms['search_term']:
                        if word in article_text:
                              save = list(row)
                              save.append(article_text)
                              relevant_text.append(save)                  
                              print('Search term found: ' +  word)
                              break
                  else: 
                        pass

                  time.sleep(5)
            else:
                  pass
      
      # Making a new DataFrame with only relavant texts
      new_df = pd.DataFrame(relevant_text[1:],columns=relevant_text[0])
      
      # Saving, as new if not exists, concating if file exists already
      save_path = DATA_PATH + 'ieee_data.csv'
      
      if path.isfile(save_path):
            old_df = pd.read_csv(save_path)
            combined_df = pd.concat([new_df, old_df])
            combined_df.drop_duplicates(subset='url', inplace=True)
            combined_df.to_csv(save_path, index=False)
      else:
            new_df.to_csv(save_path, index=False)

      # Saving collection time
      scraped_times[base_url] = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ') 
      with open(IN_DATA_PATH + 'scraped_times.json', 'w', encoding='utf8') as f:
            json.dump(scraped_times, f)

if __name__ == '__main__':
      # Paths
      dir_path = path.dirname(path.realpath(__file__))
      DATA_PATH = dir_path + '/data/'
      IN_DATA_PATH = dir_path + '/data/input_data/'
      
      # Getting last collection date, if none initializing dictionary
      try:
            with open(IN_DATA_PATH + 'scraped_times.json') as f:
                  scraped_times = json.load(f)     
      except:
            with open(IN_DATA_PATH + 'scraped_times.json', 'w', encoding='utf8') as f:
                  init_dict = {}
                  json.dump(init_dict, f)
            with open(IN_DATA_PATH + 'scraped_times.json') as f:
                  scraped_times = json.load(f)  

      # Getting base url from json
      load_file = IN_DATA_PATH + 'collection_urls_dict.json'
      with open(load_file) as handle:
            sources = json.loads(handle.read())
      base_url = sources['IEEE_spectrum']

      # Getting search terms from json
      load_file = IN_DATA_PATH + 'collection_searchterms.json'
      with open(load_file) as handle:
            search_terms = json.loads(handle.read())

      # Run
      ieee_searcher(base_url, search_terms, scraped_times)