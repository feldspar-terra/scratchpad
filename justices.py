import re
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import plotly.express as px

def get_soup(input_url,parser,find):
    url = input_url
    r = requests.get(url)
    if find == "content" :
        soup = BeautifulSoup(r.content, parser)
    else :
        soup = BeautifulSoup(r.text, parser)
    return soup

pandas_wiki_df = pd.read_html('https://en.wikipedia.org/wiki/List_of_United_States_Supreme_Court_justices_by_time_in_office')[1]
# date_errors = pandas_wiki_df[pd.to_datetime(pandas_wiki_df[pandas_wiki_df.columns[4]], errors="coerce").isna()]
# date_errors
# pandas_wiki_df[pd.to_datetime(pandas_wiki_df[pandas_wiki_df.columns[4]], errors="coerce").isna()==False]

table = get_soup('https://en.wikipedia.org/wiki/List_of_United_States_Supreme_Court_justices_by_time_in_office','html.parser','content').find( "table", {"id":"justices"} )
justices_tr = table.findAll("tr")[1:]

justice_name = []
justice_url = []
justice_term_start = []
justice_term_end = []

for justice in justices_tr:
    justice_str = justice.find_all('td')[1].text
    justice_name.append(' '.join(justice_str.split()))

    justiceurl = justice.find('a').get('href')
    justice_url.append(justiceurl)
    
    # justice_ts = justice.find_all('td')
    # justice_term_start.append(justice_ts[4].text)

    # justice_te = justice.find_all('td')
    # justice_term_end.append(justice_te[5].text)

justice_wiki_link_id = pd.DataFrame({
                                    'name': justice_name,
                                    'url': justice_url,
                    # 'term_start': justice_term_start,
                    # 'term_end':justice_term_end
                    })
# justice_wiki_link_id 

urls = []
b_date = []
d_date = []

def parseWikiDateData(wiki_date_data_str,y,m,d):
    try:
        year = wiki_date_data_str[y].replace(r"}}", "")
        month = wiki_date_data_str[m].replace(r"}}", "")
        day = wiki_date_data_str[d].replace(r"}}", "")
        date = year+"-"+month+"-"+day
    except:
        date = year+"-"+"01"+"-"+"01"
    return pd.to_datetime(date)

def get_birth_death(justice_url):
    try:
        format_justice_url = 'https://en.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&rvsection=0&titles='+justice_url.replace("/wiki/", "")+'&format=xml'
        soup = get_soup(format_justice_url,'xml','text')
        urls.append(justice_url)
        # print(justice_url.replace("/wiki/", ""))

        birth_re = re.search(r'(birth_date(.*?)}})', soup.getText())
        birth_data = birth_re.group(0).split('|')

        birth_date = parseWikiDateData(birth_data,1,2,3)
        b_date.append(birth_date)

        try:
            death_re = re.search(r'(death_date(.*?)}})', soup.getText())
            death_data = death_re.group(0).split('|')
            # print(death_data)
            if death_data[1] == r'{{death date and age':
                death_date = parseWikiDateData(death_data,2,3,4)
                d_date.append(death_date)
            elif death_data[0] > death_data[4]:
                death_date = parseWikiDateData(death_data,1,2,3)
                d_date.append(death_date)
            else:
                death_date = parseWikiDateData(death_data,4,5,6)
                d_date.append(death_date)
        except:
            d_date.append(np.nan)

    except:
        print(justice_url.replace("/wiki/", ""))
        b_date.append(np.nan)
        d_date.append(np.nan)
        

for url in justice_wiki_link_id['url']:
    get_birth_death(url)

birth_death_table = pd.DataFrame({
                                'urls': urls,
                                'b_date':b_date,
                                'd_date':d_date,
                                })
workflow_combine_df = pandas_wiki_df.merge(justice_wiki_link_id ,how="left",left_on="Justice",right_on="name").merge(birth_death_table,how="left",left_on="url",right_on="urls")
formatted_df = pd.concat([workflow_combine_df[pd.to_datetime(workflow_combine_df[workflow_combine_df.columns[4]], 
                                            errors="coerce").isna()==False]])
# formatted_df

formatted_df['start_date'] = pd.to_datetime(formatted_df[formatted_df.columns[4]], 
                                            errors="coerce")
formatted_df['end_date'] = pd.to_datetime(np.where(formatted_df[formatted_df.columns[5]]=="Incumbent",
                                    pd.to_datetime("today").strftime("%Y-%m-%d"),
                                    formatted_df[formatted_df.columns[5]]
                                    ))
formatted_df['d_date'] = np.where(formatted_df['end_date']==pd.to_datetime("today").strftime("%Y-%m-%d"),
                                    formatted_df['end_date'],
                                    formatted_df['d_date'])    
formatted_df = formatted_df.sort_values(by="end_date", ascending=False)
plotly_df = formatted_df[['Justice','start_date','end_date','b_date','d_date']]
life = plotly_df[['Justice','b_date','d_date']].copy().rename(columns={'b_date':'start_date','d_date':'end_date'})
life['task'] = 'life'
term = plotly_df[['Justice','start_date','end_date']].copy()
term['task'] = 'term'
df = pd.concat([life,term]).dropna().sort_values(by=["end_date","task"], ascending=False)
# df[df['Justice']=="Antonin Scalia"]
# df[df['start_date']>="1900-01-01"]
# df

lookup_df = life
lookup = lookup_df[lookup_df.end_date.isnull()]['Justice'].unique()
# workflow_combine_df[workflow_combine_df['Justice'].isin(lookup)]

colors = {}
colors['life'] =  'rgb(255, 0, 0)' #specify the color for the 'planned' schedule bars
colors['term'] = 'rgb(0, 0, 255)'  #specify the color for the 'actual' schedule bars

fig = px.timeline(
    df, 
    x_start="start_date", 
    x_end="end_date", 
    y="Justice",
    color='task',
    color_discrete_map = colors,
    # hover_name="Task Description"
    width=1200, height=3200
    )

# fig.update_yaxes(autorange="reversed")          #if not specified as 'reversed', the tasks will be listed from bottom up       
fig.data[1].width=0.35 # update the width of the 'Actual' schedule bars (the second trace of the figure)
fig.show()


