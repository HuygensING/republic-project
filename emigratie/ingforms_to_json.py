# -*- coding: utf-8 -*-
"""
Created on Wed Feb  1 16:22:13 2017

@author: rikhoekstra

config urls are now still hardcoded, but could work with either a local copy
or a svn checkout of an ingforms repository
"""

#import xmljson
import xmltodict
from collections import OrderedDict
#from pyld import jsonld
import os, fnmatch
from json import dump

indir = '/Users/rikhoekstra/develop/emigratie/ingforms'
defdir =  '/Users/rikhoekstra/develop/emigratie/lists/formdef'
baseurl = "http://resources.huygens.knaw.nl/"
migratieurl = "http://resources.huygens.knaw.nl/"
namespace = "huy:"
ns="huy:"


def recursive_glob(treeroot, pattern):
    results = []
    for base, dirs, files in os.walk(treeroot):
        goodfiles = fnmatch.filter(files, pattern)
        results.extend(os.path.join(base, f) for f in goodfiles)
    return results

#class JsonForm(object):
#    def __init__(self, xmlfl, typus):
#        fl = open(xmlfl)
#        rawxml = fl.read()
#        data = xmljson.parse(rawxml, process_namespaces=False)
#        self.typus = typus
#    
#    def get_context(self):
#        self.context
#  
class SchemaConverter(object):
    def __init__(self, indir=".", baseurl='.'):
        """make this a registry for later use and
        inclusion into json-ld files"""
        self.registry = {}
        self.baseurl = baseurl
        self.basedir = os.path.split(indir)[0]
        self.indir = os.path.join(self.basedir, 'lists', 'formdef')
        self.listdir = os.path.join(self.basedir, 'lists','lists')

    def schema2context(self, infile):
        baseurl =  "http://resources.huygens.knaw.nl"
        fl = open(infile)
        doc = fl.read()
        jd = xmltodict.parse(doc)
        formdef = jd['formdef']
        fields = formdef['form']
        context = {}#{'@type': os.path.join(baseurl, formdef['formkey'])}
#        if isinstance(fields['field'], str):
#            flds = [fields['field']]
#        else:
        flds = fields['field']
        for field in flds:
            fldname = formdef['formkey']
            if isinstance(field, OrderedDict):
                w_field = field
            else:
                w_field = flds
            context[w_field['key']] = os.path.join(baseurl,formdef['formkey'],w_field['key'])            
            if w_field['type'] == 'form':
                subschemanm = w_field['contents_key']
#                subschemafl = os.path.join(self.indir, subschemanm)
                subschema = self.getschema(subschemanm)
                for key in subschema['@context']:
                    context[key] = subschema['@context'][key]
        context = {"@context": context}
        return context
        
    def convert_schema(self, indir='', schemaname=''):
        """convert schema to json-ld context
        indir overrides self.indir"""
#        for item in fnmatch.filter(os.listdir(indir), '*.xml'):
        if indir == '':
            indir = self.indir
        if schemaname == 'text':
            f = os.path.join(indir, 'tekst', 'emigratie_' + schemaname + '.xml')
        else:
            f = os.path.join(indir, schemaname + '.xml')
        if os.path.exists(f):
            context = self.schema2context(f)
            nf = os.path.basename(f)
            nf = os.path.splitext(nf)[0]
            out = nf + '_jsld.json'
            flout = open(os.path.join(indir, out), 'w')
            dump( context, flout, indent=4)
            flout.close()
            self.registry[schemaname] = context

        else:
            print
            raise IOError
        
                
    def getschema(self, schemaname):
        """get schema from registry if it exists
        or put it there for later use"""
        if not self.registry.has_key(schemaname):
            self.convert_schema(schemaname=schemaname)
        outschema = self.registry.get(schemaname)
        return outschema


class JsonForm(object):
    def __init__(self, 
                 indir='', 
                 infile='',
                 url='', 
                 namespace=''):
        """parse ingforms xmlfile to json-ld
        taking a lxml etree as input"""
        self.infile = self.form2dict(infile)
        self.root = self.infile.keys()[0]
        self.registry = SchemaConverter(indir=indir, 
                                        baseurl=url)
        self.jsonfl = self.form2json(ns=namespace,
                                     schemaurl=url)

    
    def form2dict(self, infile):
        """parse ingform to python dictionary"""
        xmlt = open(infile)
        doc = xmlt.read()
        jd = xmltodict.parse(doc)
        return jd
    
    def form2json(self, ns="huy:", schemaurl="url"):
        """parse fields to json-ld 
        and add schema and namespace"""
        jd = self.infile
        root = self.root
        for key in self.infile[root].keys():
            newkey = ns + key
            jd[root][newkey] = jd[root][key]
            del jd[root][key]

        #add namespace for proper json-ld parsing
        nwk =  ns + root
        jd[nwk] = jd[root]
        del jd[root]

        jd[nwk]['@id'] = "{url}/{dit}".format(url=schemaurl, dit=root)
        for key in jd[nwk].keys():
            if key.find('_link') > -1 and jd[nwk][key]:
                if isinstance(jd[nwk][key]['relation'], list):
                    for item in jd[nwk][key]['relation']:
                        jd[nwk][key]["@id"] = "{mu}/{id}".format(mu=schemaurl,
                                                 id=item)
                else:
                    jd[nwk][key]["@id"] = "{mu}/{id}".format(mu=schemaurl,
                                                         id=jd[nwk][key].get('relation'))
                jd[nwk][key][ns+'relation'] = jd[nwk][key]['relation']
                del jd[nwk][key]['relation']
            elif jd[nwk][key] and isinstance(jd[nwk][key], OrderedDict):
                for item in jd[nwk][key].keys():
                    jd[nwk][key][ns + item] = jd[nwk][key][item]
                    del jd[nwk][key][item]

                            
        fd = self.registry.getschema(root)
        jd['@context'] = fd
        return jd
      

def convert(indir=indir,
             defdir=defdir,
             targeturl=migratieurl,
             baseurl=baseurl,
             namespace=namespace,
             ns=ns
            ):
    """convert an ingforms directory"""    
    ingforms = recursive_glob(indir,'*.xml')
    print ("forms read from %s" %indir)
    
    for item in ingforms:
        try:
            converted = JsonForm(indir,
                                 item,
                                 baseurl,
                                 namespace,
                                 )
            infl = os.path.split(item)[1]
            outfl = os.path.splitext(infl)[0] + '.json'
            outdir = indir.replace('ingforms', 'json')
            if not os.path.exists(outdir):
                os.makedirs(outdir, mode=0777)
            outf = os.path.join(outdir, outfl)
            outfl = open(outf, 'w')
            dump(converted.jsonfl, outfl, indent=4)

        except IOError:
            pass
    print ("json written to %s" %outdir)
    print ("number of files %s" % len(ingforms))        


def main(indir=indir,
             defdir=defdir,
             targeturl=migratieurl,
             baseurl=baseurl,
             namespace=namespace,
             ns=ns):
    convert(indir,defdir,targeturl,baseurl,
            namespace,ns)

if __name__ == "__main__":
    main()