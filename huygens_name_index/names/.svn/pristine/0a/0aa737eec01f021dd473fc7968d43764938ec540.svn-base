#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import re
#import difflib
#from difflib import SequenceMatcher
import Levenshtein
from names.soundex import soundexes_nl, soundex_nl
from names.common import PREFIXES, to_ascii,remove_stopwords, STOP_WORDS
#from names.memoize import cache

def split(s):
    return re.split('[ |\-]*', s)


def _average_distance_key(funcobj, l1, l2, dfunc):
    if not dfunc:
        fname = 'levenshtein'
    else:
        fname = "%s.%s" % (dfunc.__module__, dfunc.__name__)
    return "%s:%s:%s" % (fname, l1, l2)

#@cache(_average_distance_key)
def average_distance(l1, l2, distance_function=None):
        """the average distance of the words in l1 and l2
        use the distance function to compute distances between words in l1 and l2
        return the average distance of the highest scores for each of the words from both lists
        with a slight penalty for the difference in length between the lists
       
        @arguments:
            l1 is a list of strings
            l2 is a list of strings
            
        i.e.: 
        average_disatnce(['n1a', 'n1b'], ['n2'])
        is the average of :
            max(d(n1a, n2))
            max(d(n1b, n2))
            max(d(n2, n1a), d(n2,n1b))
        
        average_disatnce(['n1a', 'n1b'], ['n2a', 'n2b'])
        is the average of:
            max(d(n1a, n2a), d(n1a, n2b))
            max(d(n1b, n2a), d(n1b, n2b))
            max(d(n1a, n2a), d(n1b, n2a))
            max(d(n1a, n2b), d(n1b, n2a))
        
        """

        if not distance_function:
            distance_function = levenshtein_ratio
        counter = 0.0
        numerator = 0.0
        
        #compute array of values
#        if not l1 or not l2:
#            return 1.0
        #make l1 the shortes
        l1, l2 = len(l1)<len(l2) and (l1, l2) or (l2, l1)
        
        #compute the distrances
        distances = []
        for s1 in l1:
            distances += [(distance_function(s1, s2), s1, s2) for s2 in l2]
#            ls.sort(reverse=True)
#            distances.append((ls, s1))
        distances.sort(reverse=True)
        #compute maxima for each colum and each row
        done = set()
        for d, s1, s2 in distances:
            if s1 not in done and s2 not in done:
                done.add(s1)
                done.add(s2) 
                counter += d
                numerator += 1
        #if there is a difference in length, we penalize for each item 
        difference = len(l2) - len(l1)
        counter += .8 * difference
        numerator += difference
        if numerator == 0:
            return 1.0
        return counter/numerator

def levenshtein_ratio(a,b):
    "Calculates the Levenshtein distance between a and b."
    return Levenshtein.ratio(a,b)

# weight_normal_form = 5
# distance between soundexes of normal form (weight_normal_form / 3)
weight_normal_form_if_one_name_is_in_initials = 4 / 3
# distance between soundexes of normal form
# (weight_normal_form_soundex /1.0)
weight_normal_form_soundex_if_one_name_is_in_initials = 5/1.0
# weight_initials * 3.0
weight_initials_if_one_name_is_in_initials = 2 * 3.0
# (for example, "A.B Classen")
# (we weigh initials more in this case because we expect
# the other distances to be smaller
weight_initials_if_one_name_consists_of_one_word_only = 1



class Similarity(object):
    @staticmethod
    def levenshtein_ratio2(a, b):
        d = Levenshtein.distance(a, b)
        return 1.0 - (float(d)/10.0)

    @staticmethod
    def average_distance(l1, l2, distance_function=None): 
        return average_distance(l1, l2, distance_function)

#    def _ratio_cache_key(func, n1, n2, explain=0, optimize=False):
#        keyargs = (n1.to_string(), n2.to_string(), explain, optimize)
#        return ('%s:%s:%s:%i' % keyargs).encode('utf8')

    @staticmethod
    #@cache(_ratio_cache_key)
    def ratio(n1,n2, explain=0, optimize=False):
        """Combine several parameters do find a similarity ratio
        
        arguments:
            n1, n2 are Name instances
        returns:
            a number between 0 and 1
            
            If explain is True, it returns a string that tries to explain the way the value is computed
	        if optimize is True, skip some parts of the algorithm for speed (and sacrifice precision)"""
        weight_normal_form = 5.0 #distance between soundexes of normal form
        weight_normal_form_soundex = 8.0 #average distance between soundexes of normal form
        weight_geslachtsnaam1 = 10.0 #distance between soundexes of geslachtsnamen
        weight_geslachtsnaam2 = 10.0 #distance between geslachtsnaam
        weight_initials = 2 #distance between initials

        nf1 = n1.guess_normal_form()
        nf2 = n2.guess_normal_form()

        if not nf1 or not nf2:
            return 0.0
        elif nf1 == nf2:
            return 1.0
        ratio_normal_form = Similarity.average_distance(split(nf1), split(nf2))
        
        #create a simkplified soundex set for this name
        #remove stopwords
#        nf1 = remove_stopwords( nf1)
#        nf2 = remove_stopwords( nf2)
        
        se1 = n1.get_normal_form_soundex()
        se2 = n2.get_normal_form_soundex()
        ratio_normal_form_soundex = Similarity.average_distance( se1, se2)
        
        #gelachtsnaam wordt op twee manieren met elkaar vergeleken
        g1 = n1.geslachtsnaam() #or n1.get_volledige_naam()
        g2 = n2.geslachtsnaam() #or n2.get_volledige_naam()
        g1 = to_ascii(g1)
        g2 = to_ascii(g2)
        if not optimize:
            #de soundexes van de achternaam worden meegewoen
            #g1_soundex = n1.soundex_nl(g1, group=2, length=-1)
            g1_soundex = n1.geslachtsnaam_soundex()
            #g2_soundex = n2.soundex_nl(g2, group=2, length=-1)
            g2_soundex = n2.geslachtsnaam_soundex()
            ratio_geslachtsnaam1 = Similarity.average_distance(g1_soundex, g2_soundex)
        else:
            ratio_geslachtsnaam1 = 1 
            weight_geslachtsnaam1 = 0
            
        #n de afstand van de woorden in de achtenraam zelf
        ratio_geslachtsnaam2 = Similarity.average_distance(
             re.split('[ \.\,\-]', g1.lower()),
             re.split('[ \.\,\-]', g2.lower()),
             levenshtein_ratio)
        n1_initials = n1.initials()
        n1_initials_lower = n1_initials.lower()
        n2_initials = n2.initials()
        n2_initials_lower = n2_initials.lower()
        n1_contains_initials = n1.contains_initials()
        n2_contains_initials = n2.contains_initials()
        #count initials only if we have more than one
        #(or perhaps make this: if we know the first name)
        if len(n1_initials) == 1 or len(n2_initials) == 1:
            #initials count much less if there is only one
            weight_initials = weight_initials_if_one_name_consists_of_one_word_only
#            ratio_initials = .5
            ratio_initials = levenshtein_ratio(n1_initials_lower, n2_initials_lower)
        elif n1_contains_initials or n2_contains_initials:
            ratio_initials = levenshtein_ratio(n1_initials_lower, n2_initials_lower)
            weight_initials = weight_initials_if_one_name_is_in_initials
        elif len(n1_initials) > 1 and len(n2_initials) > 1:
            ratio_initials = levenshtein_ratio(n1_initials_lower, n2_initials_lower)
        else:
            ratio_initials = 0.7
            
        if n1_contains_initials or n2_contains_initials:
            weight_normal_form = weight_normal_form_if_one_name_is_in_initials 
            weight_normal_form_soundex = weight_normal_form_soundex_if_one_name_is_in_initials

        counter = (ratio_normal_form * weight_normal_form +
                   ratio_normal_form_soundex * weight_normal_form_soundex +
                   ratio_geslachtsnaam1 * weight_geslachtsnaam1 +
                   ratio_geslachtsnaam2 * weight_geslachtsnaam2 +
                   ratio_initials * weight_initials)
        numerator = (weight_normal_form  +  weight_normal_form_soundex +
                     weight_initials + weight_geslachtsnaam1 + weight_geslachtsnaam2)
        if numerator == 0:
            return 0.0
        final_ratio = counter/numerator

        if explain:
            s = '-' * 100 + '\n'
            s += 'Naam1: %s [%s] [%s] %s\n' % (n1, n1_initials, n1.guess_normal_form(), se1)
            s += 'Naam2: %s [%s] [%s] %s\n' % (n2, n2_initials, n2.guess_normal_form(), se2)
            s += 'Similarity ratio: %s\n' % final_ratio
            s += '--- REASONS'  + '-' * 30 + '\n'
            format_s = '%-30s | %-10s | %-10s | %-10s | %-10s | %s-10s\n'
            s += format_s % ('\t  property', '  ratio', '  weight','relative_weight',  '  r*w', 'r * relative_w')
            s += '\t' + '-' * 100 + '\n'
            format_s = '\t%-30s | %-10f | %-10f | %-10f | %-10f | %-10f\n'
            s += format_s % (' normal_form', ratio_normal_form, weight_normal_form,weight_normal_form/counter, ratio_normal_form * weight_normal_form, ratio_normal_form * weight_normal_form/counter)
            s += format_s % ('soundex van normal_form', ratio_normal_form_soundex, weight_normal_form_soundex,weight_normal_form_soundex/counter, ratio_normal_form_soundex* weight_normal_form_soundex, ratio_normal_form_soundex * weight_normal_form_soundex/counter)
            s += format_s % ('soundex van geslachtsnaam1', ratio_geslachtsnaam1, weight_geslachtsnaam1,weight_geslachtsnaam1/counter, ratio_geslachtsnaam1 * weight_geslachtsnaam1, ratio_geslachtsnaam1 * weight_geslachtsnaam1/counter)
            s += format_s % ('geslachtsnaam', ratio_geslachtsnaam2, weight_geslachtsnaam2,weight_geslachtsnaam2/counter,  ratio_geslachtsnaam2 *weight_geslachtsnaam2 , ratio_geslachtsnaam2 * weight_geslachtsnaam2/counter)
            s += format_s % ('initials', ratio_initials, weight_initials, weight_initials/counter, ratio_initials *weight_initials, ratio_initials * weight_initials/counter)
            s += '\tTOTAL  (numerator)                                       | %s (counter = %s)\n' %  (counter, numerator)
            
            return s
        return final_ratio

    def explain_ratio(self, n1, n2):
        return Similarity.ratio(n1, n1, explain=1) 
    

