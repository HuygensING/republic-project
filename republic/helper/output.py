from IPython.display import HTML
htmlout = []

out = []
for T in searchobs:
    ob = searchobs[T]
    out.append(ob.to_dict())
# with open('/Users/rikhoekstra/Downloads/1728_pres2.json', 'w') as fp:
json_year = json.dumps(obj=out)


jsondelegates = abbreviated_delegates.loc[abbreviated_delegates.id.isin(previously_matched.id)]


# In[183]:


jsondelegates.columns


# In[185]:


jsondelegates.rename(columns={"h_life": "hypothetical_life", "p_interval":"period_active", "sg": "active_stgen"},
                     inplace=True)


# In[186]:


for lj in ['geboortejaar', 'sterfjaar']:
    jsondelegates[lj] = jsondelegates[lj].dt.strftime("%Y-%m-%d")


# In[187]:


interval = pd.Interval(left=1820,right=1890, closed="both")
interval.left


# In[188]:


for interval in ["hypothetical_life", "period_active"]:
    jsondelegates[interval]=jsondelegates[interval].apply(lambda x: [x.left, x.right])


jsondelegates.rename(columns={"h_life": "hypothetical_life", "p_interval": "period_active", "sg": "active_stgen"},
                     inplace=True)

delegate_json = serializable_df[['ref_id', 'name', 'geboortejaar', 'sterfjaar', 'colleges',
                                 'functions', 'active_stgen', 'was_gedeputeerde',
                                 'period_active', 'hypothetical_life']].to_json(orient="records")

with open("/Users/rikhoekstra/Downloads/delegats.json", 'w') as fp:
    fp.write(delegate_json)

for T in searchobs:
    ob = searchobs[T].matched_text
    url = searchobs[T].make_url()
    ob.mapcolors()
    rest = ob.serialize()
    rest = f"\n<h4>{T}</h4>\n" + rest
    if url:
        rest += f"""<br/><br/><a href='{url}'>link naar {T}-image</a><br/>"""
    htmlout.append(rest)
#out.reverse()
HTML("<br><hr><br>".join(htmlout))

from IPython.display import HTML
htmlout=[]
for T in searchobs:
    ob = searchobs[T].matched_text
    url = searchobs[T].make_url()
    ob.mapcolors()
    rest = ob.serialize()
    rest = f"\n<h4>{T}</h4>\n" + rest
    if url:
        rest += f"""<br/><br/><a href='{url}'>link naar {T}-image</a><br/>"""
    htmlout.append(rest)
#out.reverse()
HTML("<br><hr><br>".join(htmlout))

# In[68]:


from IPython.display import HTML
t_out=[]
for T in searchobs:
    ob = searchobs[T].matched_text
    url = searchobs[T].make_url()
    ob.mapcolors()
    rest = ob.serialize()
    rest = f"""\n<tr><td><strong>{T}</strong></td><td>{rest}</td>"""
    if url:
        rest += f"""<td><a href='{url}'>link naar {T}-image</a></td>"""
    rest += "</tr>"
    t_out.append(rest)
#out.reverse()
outtable = "".join(t_out)
HTML(f"<table>{outtable}</table>")


# In[69]:


with open(f"/Users/rikhoekstra/Downloads/{day}_check.html", 'w') as flout:
    flout.write(f"<html><body><h1>results for {day}</h1>\n")
    flout.write(f"<table>{outtable}</table>")
    flout.write("</body></html>")

for T in searchobs:
    search_results = {}
    ob = searchobs[T].matched_text
    unmarked_text = ''.join(ob.get_unmatched_text())
    splittekst = re.split(pattern="\s",string=unmarked_text)
    for s in splittekst:
        if len(s)>2 and len(junksweeper.find_candidates(s))==0:
            sr = identified.get(s)
            try:
                if len(sr) > 0:
                    sr = sr.loc[sr.score == sr.score.max()]
                    nm = sr.name.iat[0]
                    idnr = sr.id.iat[0]
                    score = sr.score.max()
                    b = ob.item.find(s)
                    e = b + len(s)
                    span = ob.set_span(span=(b,e), clas='delegate', pattern=s, delegate=idnr, score=score)
                    search_results.update({s:{'match_term':nm, 'match_string':s, 'score': score}, 'spandid':span})
            except TypeError:
                pass# "naam": {
#                         "properties":{
#                             'geslachtsnaam': {"type":"string"},
#                             'fullname': {"type":"string"},
#                             'birth': {"type":"string"},
#                             'death': {"type":"string"},
#                             'by': {"type":"integer"},
#                             'dy': {"type":"integer"},
#                             'bp': {"type":"string"},
#                             'dp': {"type":"string"},
#                             'biography': {"type":"text"},
#                             'reference': {"type":"string"}
#                         }
#                     },
#         }
#
# att_lst_mapping = {
#     "mappings": {
#         "properties": {
#                  'metadata':{"properties":{
#                            "coords":{"properties":{
#                                  'bottom': {"type":"int"},
#                                  'height': {"type":"int"},
#                                  'left': {"type":"int"},
#                                  'right': {"type":"int"},
#                                  'top': {"type":"int"},
#                                  'width': {"type":"int"}
#                                },
#                             'inventory_num':{"type": "int"},
#                             'meeting_lines':{"type": "string"},
#                             'text':{"type":"string"},
#                             'zittingsdag_id':{"type":"string"},
#                             'url':{"type":"string"}
#                            }
#                          }
#                         }
#                     },
#                  'spans': {"properties":{
#                            'offset':{"type":"integer"},
#                              'end':{"type":"integer"},
#                              'pattern':{"type":"string"},
#                              'class':{"type":"string"},
#                              'delegate_id':{"type":"string"},
#                              'delegate_name':{"type":"string"},
#                              'delegate_score':{"type":"float"}}
#                            }
#             }
#     }

# ## To Elasticsearch

# In[70]:


from republic.republic_keyword_matcher.elastic_search_helpers import bulk_upload
local_republic_es = Elasticsearch()
local_republic_es


# In[ ]:


local_republic_es.indices.create(index='attendancelist')


# In[ ]:


data_dict = out
bulk_upload(bulkdata=data_dict, index='attendancelist', doctype='attendancelist')

