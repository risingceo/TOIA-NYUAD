# -*- coding: utf-8 -*-

'''Libraries
'''

import string
import re
from collections import defaultdict
from fractions import Fraction
import json
import time
import datetime
import copy
import random

import os
import sys

#path to Arabic NLP tools
sys.path.insert(0, 'dialogue-manager/CalimaStar_files/')


import StarMorphModules
import StopWords
import nltk
import ssl
import math

# import the English NLP tools and corpuses from the NLTK library
nltk.download('wordnet')
from nltk.stem.porter import PorterStemmer
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from string import punctuation
from nltk.corpus import wordnet as wn
nltk.download('stopwords')


try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context



'''
class databaseEntry:
    the structure/blueprint for a video object

'''
class databaseEntry:
    def __init__(self, question, answer, video, avatar, language, frequency):
        # avatar: the name of the avatar associated with the video
        self.avatar = avatar

        # question: the question string that the video is a response to
        self.question = question

        # answer: the response/answer to the question
        self.answer = answer

        #videoLink: the pathway of the recorded video
        self.videoLink = video

        # lanuage: the name of the language of the recorded vide
        self.language = language

        # frequency: the number of times a video can be played specified by the user. The options include: once, never and multiple
        self.frequency = frequency

        # questionLength: the number of words in the question
        self.questionLength = len(question.split())

        # answerLength: the number of words in the answer/response
        self.answerLength = len(answer.split())

    # toString(self): prints the avatar, question, answer and the language of the recorded video
    def toString(self):
        print( self.avatar, ": \n", self.question, "\n", self.answer, "\n", self.language, "\n")



'''
class model:
    The structure/blueprint for an avatar's model object

'''
class model:

    def __init__(self):
        # stemmedMap: a dictionary where the keys are the stems of all words in the avatar's question-answer pairs and tha values map to the videoIDs of the pairs in which the respective word appears
        self.stemmedMap = {}

        # lemmatizeddMap: a dictionary where the keys are the lemma of all words in the avatar's question-answer pairs and tha values map to the videoIDs of the pairs in which the respective word appears
        self.lemmatizedMap = {}

        # wordMap: a dictionary where the keys are all of the words in the avatar's question-answer pairs and tha values map to the videoIDs of the pairs in which the respective word appears
        self.wordMap = {}

        # objectMap: a dictionary of all the databaseEntry objects
        self.objectMap = {}

        # noAnswer: the dictionary of databaseEntry of the avatar saying "I can't answer that"
        self.noAnswer= {}



'''
class session:
    the structure/blueprint of the session. where each session is the complete dialogue between the avatar and the user

'''
class session:

    def __init__(self, avatar, language):
        # repetitions: the dictionary where the keys are the videoID of the videos of the videos which have been played in the session and the values are the number of times the respective video has been played
        self.repetitions = {}

        # currentAvatar: the avatar that the user is currently interacting with
        self.currentAvatar = avatar

        #language: the language in which the user is interacting with the avatar
        self.language = language


'''
Global Variables
'''
# porterStemmer: Porter Stemmer used for stemming the english words
porterStemmer = PorterStemmer()

#lemmatizer: Wordnet Lemmatizer used for lemmatizing the english words
lemmatizer = WordNetLemmatizer()

#avatar model stores the avatar model object of all avatars  
avatarModel = {}

#database filename
db= ''

av_length=0

av_accuracy=0

# encoding
str.encode('utf-8')


# find the intersection of two lists
def intersect(a, b):
    return list(set(a) & set(b))


# preprocessing for Arabic
def preprocess(line):
    processed = line.replace("؟", "")
    processed = line.replace(".", "")
    processed = line.replace("،", "")
    processed = processed.replace("أ", "ا")
    processed = processed.replace("إ", "ا")
    processed = processed.replace("ى", "ي")
    processed = processed.replace("ة", "ه")

    return processed

# save configuration variables from avatar's json files
def configure(avatar_accuracy, avatar_length):

    if (avatar_accuracy=="high"):
        av_accuracy= 0.1
    elif (avatar_accuracy=="low"):
        av_accuracy= 0.001
    else:
        av_accuracy=0
    
    av_length=avatar_length 

    return av_length, av_accuracy

#generate stop words

def getStopwords(language):
    stop_words= []
    if language=="English":
        stop_words = stopwords.words('english') + list(punctuation)
        #stop_words += ["on", "in", "tell", "me", "about", "a", "an", "the", "of", "and", "or", "but", "what", "are", "you", "your", "is", "was" , "do"]

    elif language== "Arabic":
       stop_words= StopWords.getStopwords()
   
    return stop_words

#get Arabic synonyms
def arabicSyn(myavatar):

    db= 'static/avatar-garden/' + myavatar +'/script.json'

    glossDict={}
    synonymDict={}
    unigram_synonyms_list = []

    f = open(db, 'r', encoding='utf-8')

    resp = json.load(f)

    for i in range(0, len(resp["rows"]) - 1, 1):
        if ("arabic-question" in resp["rows"][i]["doc"].keys() and "arabic-answer" in resp["rows"][i]["doc"].keys()):
            question = json.dumps(resp["rows"][i]["doc"]["arabic-question"], ensure_ascii=False).strip('،.؟"')
            answer = json.dumps(resp["rows"][i]["doc"]["arabic-answer"], ensure_ascii=False).strip('،.؟"')

            pair= question.split()+answer.split()

            for tmp in pair:
                gloss=StarMorphModules.analyze_word(tmp, False)[0].split()[4].split(";")[0].replace("gloss:", "")
                if gloss not in glossDict.keys() and gloss != "NO_ANALYSIS":
                    glossDict[gloss]= []
                    glossDict[gloss].append(tmp)
                elif gloss in glossDict.keys() and gloss != "NO_ANALYSIS":
                    if tmp not in glossDict[gloss]:
                        glossDict[gloss].append(tmp)

    for key in glossDict.keys():
        if len(glossDict[key])>1:
            for i in glossDict[key]:
                if i not in synonymDict.keys():
                    synonymDict[i]=[j for j in glossDict[key]]
    return synonymDict


# Initiates the model and create a new session
def createModel(avatarModel, currentSession, mylanguage, test_par):


    #db is the path to the json file containing the question-answer pairs of the specified avatar (my avatar)
    db= 'static/avatar-garden/' + myavatar +'/script.json'
    try:
        f = open(db, 'r', encoding='utf-8')
    except IOError:
        print("Error: File does not appear to exist.")

    resp = json.load(f)
   
    #number of questions in the db, used for debugging purposes  
    totalQuestions = 0

    #ID: counter to automatically generate ID for each databaseEntry in the model
    ID = 0


    if mylanguage=="Arabic":
        arabic_synonyms= arabicSyn(myavatar)

    for i in range(0, len(resp["rows"]) - 1, 1):

        #automatically generated ID 
        ID += 1

        totalQuestions += 1


        video = json.dumps(resp["rows"][i]["doc"]["video"])
        # avatar= json.dumps(resp["rows"][i]["doc"]["avatar"])
        #variable that stores the avatar name
        avatar = json.dumps(resp["rows"][i]["doc"]["video"]).split("_")[0].replace('"', '')

        #variable that stores the language that the avatar videos were recorded in 
        language = json.dumps(resp["rows"][i]["doc"]["language"])
        #variable that stores the user's preferred playing frequency for each database entry
        frequency= json.dumps(resp["rows"][i]["doc"]["playing frequency"])


        if (mylanguage == "Arabic"):
            
            question = json.dumps(resp["rows"][i]["doc"]["arabic-question"], ensure_ascii=False)
            answer = json.dumps(resp["rows"][i]["doc"]["arabic-answer"], ensure_ascii=False)
            question= preprocess(question)
            answer= preprocess(answer)

        if (mylanguage == "English"):
            question = json.dumps(resp["rows"][i]["doc"]["english-question"]).strip(',?."!)')
            answer = json.dumps(resp["rows"][i]["doc"]["english-answer"]).strip(',?."!)')

        # Creates a new avatar model object in the avatarModel if it does not exist already
        if avatar not in avatarModel.keys():
            # avatarModel[avatar] is the model of the respective avatar
            avatarModel[avatar] = model()


        #save configuration variables

        '''
        accuracy (low/medium/high): This value is used as a threshold for accuracy. For example, if you require videos to be played only when there is a high match, then select "High". Otherwise, select either "Low" or "Medium". The default value is "Low".
        length constant: if the number of words in an aswer is above this constant, then these answers will be ranked lower in our question-answer matching algorithm. 
        video type: a tag that either equals regular, or filler, according to the type of the database entry
        '''
        accuracy= json.dumps(resp["rows"][i]["doc"]["minimum required accuracy"])
        maxLength= json.dumps(resp["rows"][i]["doc"]["length constant"])
        videoType= json.dumps(resp["rows"][i]["doc"]["video-type"])

        #read the configuration variables from the database and save it to the global variables
        configure(accuracy, maxLength)


        # obj: creates the databaseEntry object for the recorded video and adds it to the objectMap in the avatarModel
        obj = databaseEntry(question, answer, video, avatar, language, frequency)
        avatarModel[avatar].objectMap[ID] = obj



        '''If the videoType tag of the database entry is no-answer, the avatar says "I can't answer that" in this video
         it's added to the noAnswer property of the avatarModel'''
        if(videoType== '"no-answer"'):
            avatarModel[avatar].noAnswer[ID] = obj

        # stemming the question and answer and adding the stems, their bigrams and trigrams into model.stemmedMap
        if (mylanguage == "English"):

            unigram_split = question.lower().split() + answer.lower().split()
            unigram_list = [tmp.strip(',?."!)') for tmp in unigram_split]
            unigram_synonyms_list = []

            # expands the unigram model by adding synonyms
            if test_par.synonym == True:
                for word in unigram_list:
                    #if word not in stop_words:
                    for synset in wn.synsets(word):
                        for lemma in synset.lemmas():
                            if lemma.name() not in unigram_synonyms_list and lemma.name() not in unigram_list:
                                unigram_synonyms_list.append(lemma.name())

            # add the bigrams and trigrams into the three representations
            totalUnigrams = len(unigram_list)

            for i in range(totalUnigrams):

                # creates bigrams, their stems and lemmas and adds them to the respective maps
                if test_par.bigram == True:
                    if i < totalUnigrams - 1:

                        bigram = unigram_list[i] + "_" + unigram_list[i + 1]
                        if bigram not in avatarModel[avatar].wordMap.keys():
                            avatarModel[avatar].wordMap[bigram] = {}
                        if ID not in avatarModel[avatar].wordMap[bigram]:
                            avatarModel[avatar].wordMap[bigram][ID] = 1
                        else:
                            avatarModel[avatar].wordMap[bigram][ID] += 1

                        bigram_stem = porterStemmer.stem(unigram_list[i]) + "_" + porterStemmer.stem(unigram_list[i + 1])
                        if bigram_stem not in avatarModel[avatar].stemmedMap.keys():
                            avatarModel[avatar].stemmedMap[bigram_stem] = {}
                        if ID not in avatarModel[avatar].stemmedMap[bigram_stem]:
                            avatarModel[avatar].stemmedMap[bigram_stem][ID] = 1
                        else:
                            avatarModel[avatar].wordMap[bigram][ID] += 1

                        bigram_lemma = lemmatizer.lemmatize(unigram_list[i]) + "_" + lemmatizer.lemmatize(
                            unigram_list[i + 1])
                        if bigram_lemma not in avatarModel[avatar].lemmatizedMap.keys():
                            avatarModel[avatar].lemmatizedMap[bigram_lemma] = {}
                        if ID not in avatarModel[avatar].lemmatizedMap[bigram_lemma]:
                            avatarModel[avatar].lemmatizedMap[bigram_lemma][ID] = 1
                        else:
                            avatarModel[avatar].lemmatizedMap[bigram_lemma][ID] += 1

                # creates trigrams, their stems and lemmas and add them to the respective maps
                if test_par.trigram == True:
                    if i < totalUnigrams - 2:

                        trigram = unigram_list[i] + "_" + unigram_list[i + 1] + "_" + unigram_list[i + 2]
                        if trigram not in avatarModel[avatar].wordMap.keys():
                            avatarModel[avatar].wordMap[trigram] = {}
                        if ID not in avatarModel[avatar].wordMap[trigram]:
                            avatarModel[avatar].wordMap[trigram][ID] = 1
                        else:
                            avatarModel[avatar].wordMap[trigram][ID] = +1

                        trigram_stem = porterStemmer.stem(unigram_list[i]) + "_" + porterStemmer.stem(
                            unigram_list[i + 1]) + "_" + porterStemmer.stem(unigram_list[i + 2])
                        if trigram_stem not in avatarModel[avatar].stemmedMap.keys():
                            avatarModel[avatar].stemmedMap[trigram_stem] = {}
                        if ID not in avatarModel[avatar].stemmedMap[trigram_stem]:
                            avatarModel[avatar].stemmedMap[trigram_stem][ID] = 1
                        else:
                            avatarModel[avatar].stemmedMap[trigram_stem][ID] += 1

                        trigram_lemma = lemmatizer.lemmatize(unigram_list[i]) + "_" + lemmatizer.lemmatize(
                            unigram_list[i + 1]) + "_" + lemmatizer.lemmatize(unigram_list[i + 2])
                        if trigram_lemma not in avatarModel[avatar].lemmatizedMap.keys():
                            avatarModel[avatar].lemmatizedMap[trigram_lemma] = {}
                        if ID not in avatarModel[avatar].lemmatizedMap[trigram_lemma]:
                            avatarModel[avatar].lemmatizedMap[trigram_lemma][ID] = 1
                        else:
                            avatarModel[avatar].lemmatizedMap[trigram_lemma][ID] += 1


            # removes stop words
            # question_split = [tmp.strip(', " ?.!') for tmp in question_split if tmp not in stop_words]
            # answer_split = [tmp.strip(', " ?.!') for tmp in answer_split if tmp not in stop_words]

            # adds the unigrams and their synonyms into the three hashmaps - stems, lemmas and direct:

            ''' 
            1. avatarModel[avatar].wordMap is a dictionary where the key is the word 
            and the value is another dictionary with video IDs as keys, and the number of times that the word appears in that video as values
            
            2. avatarModel[avatar].stemmedMap is a dictionary where the key is the stem of a word 
            and the value is another dictionary with video IDs as keys, and the number of times that the word appears in that video as values

            3. avatarModel[avatar].LemmatizedMap is a dictionary where the key is the word (either unigram, bigram, or trigram)
            and the value is another dictionary with video IDs as keys, and the number of times that the word appears in that video as values
            '''

            if test_par.unigram == True:
                for token in (unigram_list+unigram_synonyms_list):
                    

                    stem = porterStemmer.stem(token)
                    lemma = lemmatizer.lemmatize(token)

                    if token not in avatarModel[avatar].wordMap.keys():
                        avatarModel[avatar].wordMap[token] = {}
                    if ID not in avatarModel[avatar].wordMap[token].keys():
                        avatarModel[avatar].wordMap[token][ID] = 1
                    else:
                        avatarModel[avatar].wordMap[token][ID] += 1
                    #print("token" + " " + token, avatarModel[avatar].wordMap[token])

                    if stem not in avatarModel[avatar].stemmedMap.keys():
                        avatarModel[avatar].stemmedMap[stem] = {}
                    if ID not in avatarModel[avatar].stemmedMap[stem]:
                        avatarModel[avatar].stemmedMap[stem][ID] = 1
                    else:
                        avatarModel[avatar].stemmedMap[stem][ID] += 1

                    if lemma not in avatarModel[avatar].lemmatizedMap.keys():
                        avatarModel[avatar].lemmatizedMap[lemma] = {}
                    if ID not in avatarModel[avatar].lemmatizedMap[lemma]:
                        avatarModel[avatar].lemmatizedMap[lemma][ID] = 1
                    else:
                        avatarModel[avatar].lemmatizedMap[lemma][ID] += 1


                    avatarModel[avatar].wordMap[token][ID]= avatarModel[avatar].wordMap[token][ID]/totalUnigrams
                    avatarModel[avatar].stemmedMap[stem][ID]= avatarModel[avatar].stemmedMap[stem][ID]/totalUnigrams
                    avatarModel[avatar].lemmatizedMap[lemma][ID]= avatarModel[avatar].stemmedMap[stem][ID]/totalUnigrams

        elif (mylanguage == "Arabic"):

            #arabic_stop_words= getStopwords("Arabic")

            unigram_split = question.strip('،"!؟/)').replace("،", " ").replace("/", " ").split() + answer.strip('،"!؟/)').replace("،", " ").replace("/", " ").split()

            unigram_list = [tmp.strip('،"!؟/)').replace('/', '') for tmp in unigram_split]

            unigram_synonyms_list = []


            # expands the unigram model by adding synonyms
            if (test_par.synonym == True):
                for word in unigram_list:
                    if word in arabic_synonyms.keys():
                        for tmp in arabic_synonyms[word]:
                            if tmp not in unigram_synonyms_list:
                                unigram_synonyms_list.append(tmp)

            totalUnigrams = len(unigram_list)

            # add the bigrams and trigrams into the three representations

            for i in range(totalUnigrams):

                # creates bigrams, their stems and lemmas and adds them to the respective maps
                if test_par.bigram == True:
                    if (i < totalUnigrams - 1):
                    bigram = unigram_list[i] + "_" + unigram_list[i + 1]
                    if bigram not in avatarModel[avatar].wordMap.keys():
                        avatarModel[avatar].wordMap[bigram] = {}
                    if ID not in avatarModel[avatar].wordMap[bigram]:
                        avatarModel[avatar].wordMap[bigram][ID] = 1
                    else:
                        avatarModel[avatar].wordMap[bigram][ID] += 1

                    bigram_stem = StarMorphModules.analyze_word(unigram_list[i], False)[0].split()[1].replace("stem:", "").split('d',1)[0] + "_" + StarMorphModules.analyze_word(unigram_list[i+1], False)[0].split()[1].replace("stem:", "").split('d',1)[0]

                    if bigram_stem not in avatarModel[avatar].stemmedMap.keys():
                        avatarModel[avatar].stemmedMap[bigram_stem] = {}
                    if ID not in avatarModel[avatar].stemmedMap[bigram_stem]:
                        avatarModel[avatar].stemmedMap[bigram_stem][ID] = 1
                    else:
                        avatarModel[avatar].wordMap[bigram][ID] += 1

                    bigram_lemma = StarMorphModules.analyze_word(unigram_list[i], False)[0].split()[0].replace("lex:", "").split('_',1)[0] + "_" + StarMorphModules.analyze_word(unigram_list[i+1], False)[0].split()[0].replace("lex:", "").split('_',1)[0]

                    if bigram_lemma not in avatarModel[avatar].lemmatizedMap.keys():
                        avatarModel[avatar].lemmatizedMap[bigram_lemma] = {}

                    if ID not in avatarModel[avatar].lemmatizedMap[bigram_lemma]:
                        avatarModel[avatar].lemmatizedMap[bigram_lemma][ID] = 1
                    else:
                        avatarModel[avatar].lemmatizedMap[bigram_lemma][ID] += 1

                # creates trigrams, their stems and lemmas and add them to the respective maps
                if test_par.trigram == True:
                    if i < totalUnigrams - 2:
                    trigram = unigram_list[i] + "_" + unigram_list[i + 1] + "_" + unigram_list[i + 2]

                    if trigram not in avatarModel[avatar].wordMap.keys():
                        avatarModel[avatar].wordMap[trigram] = {}
                    if ID not in avatarModel[avatar].wordMap[trigram]:
                        avatarModel[avatar].wordMap[trigram][ID] = 1
                    else:
                        avatarModel[avatar].wordMap[trigram][ID] = +1

                    trigram_stem =  StarMorphModules.analyze_word(unigram_list[i], False)[0].split()[1].replace("stem:", "").split('d',1)[0] + "_" + StarMorphModules.analyze_word(unigram_list[i+1], False)[0].split()[1].replace("stem:", "").split('d',1)[0]+ "_" + StarMorphModules.analyze_word(unigram_list[i+2], False)[0].split()[1].replace("stem:", "").split('d',1)[0]
                    if trigram_stem not in avatarModel[avatar].stemmedMap.keys():
                        avatarModel[avatar].stemmedMap[trigram_stem] = {}
                    if ID not in avatarModel[avatar].stemmedMap[trigram_stem]:
                        avatarModel[avatar].stemmedMap[trigram_stem][ID] = 1
                    else:
                        avatarModel[avatar].stemmedMap[trigram_stem][ID] += 1

                    trigram_lemma = StarMorphModules.analyze_word(unigram_list[i], False)[0].split()[0].replace("lex:", "").split('_',1)[0] + "_" + StarMorphModules.analyze_word(unigram_list[i+1], False)[0].split()[0].replace("lex:", "").split('_',1)[0] + "_" + StarMorphModules.analyze_word(unigram_list[i+2], False)[0].split()[0].replace("lex:", "").split('_',1)[0]
                    if trigram_lemma not in avatarModel[avatar].lemmatizedMap.keys():
                        avatarModel[avatar].lemmatizedMap[trigram_lemma] = {}
                    if ID not in avatarModel[avatar].lemmatizedMap[trigram_lemma]:
                        avatarModel[avatar].lemmatizedMap[trigram_lemma][ID] = 1
                    else:
                        avatarModel[avatar].lemmatizedMap[trigram_lemma][ID] += 1rdict[character].lemmatizedMap[trigram_lemma][ID] += 1

            # adds the unigrams and their synonyms into the three hashmaps - stems, lemmas and direct + unigram_synonyms_list:
            if test_par.unigram == True:
                for token in (unigram_list+ unigram_synonyms_list):
                stem = StarMorphModules.analyze_word(token, False)[0].split()[1].replace("stem:", "").split('d',1)[0]
                lemma = StarMorphModules.analyze_word(token, False)[0].split()[0].replace("lex:", "").split('_',1)[0]

                if token not in avatarModel[avatar].wordMap.keys():
                    avatarModel[avatar].wordMap[token] = {}
                if ID not in avatarModel[avatar].wordMap[token]:
                    print(ID, token)
                    avatarModel[avatar].wordMap[token][ID] = 1
                else:
                    print("second time", ID, token)
                    avatarModel[avatar].wordMap[token][ID] += 1

                if stem not in avatarModel[avatar].stemmedMap.keys():
                    avatarModel[avatar].stemmedMap[stem] = {}
                if ID not in avatarModel[avatar].stemmedMap[stem]:
                    avatarModel[avatar].stemmedMap[stem][ID] = 1
                else:
                    avatarModel[avatar].stemmedMap[stem][ID] += 1

                if lemma not in avatarModel[avatar].lemmatizedMap.keys():
                    avatarModel[avatar].lemmatizedMap[lemma] = {}
                if ID not in avatarModel[avatar].lemmatizedMap[lemma]:
                    avatarModel[avatar].lemmatizedMap[lemma][ID] = 1
                else:
                    avatarModel[avatar].lemmatizedMap[lemma][ID] += 1

    print("number of times name appears in video 1:" , avatarModel[avatar].wordMap["name"][1])

    print("Total Questions: ", str(totalQuestions))
    print("done")
    # print(avatarModel["gabriela"].wordMap)
    #print("before",avatarModel['margarita'].wordMap['hello'])
    calculateTFIDF(avatarModel)
    #print("avatar dictionary", avatarModel['margarita'])
    #print("after", avatarModel['margarita'].wordMap['hello'])
    return currentSession



def direct_intersection_match_English(query, characterModel, test_par, logger):
    stop_words= []
    queryList = [tmp.strip(', " ?.!)') for tmp in query.split() if tmp not in stop_words ]
    responses = {}
    queryLen = len(queryList)
    tokens_used = []

    # newList = []

    # #expands the unigram model by adding synonyms
    # for word in queryList:
    # 	#if word not in stop_words:
    # 	for synset in wn.synsets(word):
    # 		for lemma in synset.lemmas():
    # 			if lemma.name() not in newList:
    # 				newList.append(lemma.name())

    for i in range(queryLen):

        if test_par.unigram == True:
            unigram_string = queryList[i]
            if unigram_string in avatarModel.wordMap.keys() and unigram_string not in tokens_used:  # and direct_string not in stop_words:
                tokens_used.append(unigram_string)
                #print("word: ", unigram_string)
                #print("word map: ", avatarModel.wordMap[unigram_string])
                for obj_videoID in avatarModel.wordMap[unigram_string]:
                    #print("videos that include ",unigram_string, obj_videoID )
                    if obj_videoID not in responses.keys():
                        responses[obj_videoID] = avatarModel.wordMap[unigram_string][obj_videoID]
                        #print("added video "+ str(obj_videoID) + "to responses" + " its value is " + str(avatarModel.wordMap[unigram_string][obj_videoID]))
                    else:
                        responses[obj_videoID] += avatarModel.wordMap[unigram_string][obj_videoID]
                        #print("increased score of " + str(obj_videoID) + "by " + str(avatarModel.wordMap[unigram_string][obj_videoID]))
                    if obj_videoID not in logger.keys():
                        logger[obj_videoID] = {}
                        logger[obj_videoID][unigram_string] = avatarModel.wordMap[unigram_string][obj_videoID]
                    else:
                        if unigram_string in logger[obj_videoID]:
                            logger[obj_videoID][unigram_string] += avatarModel.wordMap[unigram_string][obj_videoID]
                        else:
                            logger[obj_videoID][unigram_string] = avatarModel.wordMap[unigram_string][obj_videoID]

        if test_par.bigram == True:
            if i < queryLen - 2:
                bigram_string = queryList[i] + "_" + queryList[i + 1]
                if bigram_string in characterModel.wordMap.keys():  # and direct_string not in stop_words:
                    for vidResponse in characterModel.wordMap[bigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.wordMap[bigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.wordMap[bigram_string][vidResponse]

        if test_par.trigram == True:
            if i < queryLen - 3:
                trigram_string = queryList[i] + "_" + queryList[i + 1] + "_" + queryList[i + 2]
                if trigram_string in characterModel.wordMap.keys():  # and direct_string not in stop_words:
                    for vidResponse in characterModel.wordMap[trigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.wordMap[trigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.wordMap[trigram_string][vidResponse]

    # for direct_string in queryList:
    #     if direct_string in characterModel.wordMap.keys():  # and direct_string not in stop_words:
    #         for vidResponse in characterModel.wordMap[direct_string]:
    #             if vidResponse not in responses.keys():
    #                 responses[vidResponse] = characterModel.wordMap[direct_string][vidResponse]
    #             elif vidResponse in responses.keys():
    #                 responses[vidResponse] += characterModel.wordMap[direct_string][vidResponse]

    print("English direct responses", responses)
    for key in responses.keys():
        responses[key]= responses[key]

    return responses


def stem_intersection_match_English(query, characterModel, test_par, logger):
    queryList = [porterStemmer.stem(tmp.strip(', " ?.!)')) for tmp in query.split()]

    responses = {}

    queryLen = len(queryList)

    for i in range(queryLen):

        if test_par.unigram == True:

            unigram_string = stemmed_query[i]
            if unigram_string in avatarModel.stemmedMap.keys() and unigram_string not in tokens_used:
                tokens_used.append(unigram_string)
                for obj_videoID in avatarModel.stemmedMap[unigram_string]:
                    if obj_videoID not in responses.keys():
                        responses[obj_videoID] = avatarModel.stemmedMap[unigram_string][obj_videoID]
                    else:
                        responses[obj_videoID] += avatarModel.stemmedMap[unigram_string][obj_videoID]

                    if obj_videoID not in logger.keys():
                        logger[obj_videoID] = {}
                        logger[obj_videoID][unigram_string] = avatarModel.stemmedMap[unigram_string][obj_videoID]
                    else:
                        if unigram_string in logger[obj_videoID]:
                            logger[obj_videoID][unigram_string] += avatarModel.stemmedMap[unigram_string][obj_videoID]
                        else:
                            logger[obj_videoID][unigram_string] = avatarModel.stemmedMap[unigram_string][obj_videoID]

        if test_par.bigram == True:
            if i < queryLen - 2:
                bigram_string = queryList[i] + "_" + queryList[i + 1]
                if bigram_string in characterModel.stemmedMap.keys():
                    for vidResponse in characterModel.stemmedMap[bigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.stemmedMap[bigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.stemmedMap[bigram_string][vidResponse]

        if test_par.trigram == True:
            if i < queryLen - 3:
                trigram_string = queryList[i] + "_" + queryList[i + 1] + "_" + queryList[i + 2]
                if trigram_string in characterModel.stemmedMap.keys():
                    for vidResponse in characterModel.stemmedMap[trigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.stemmedMap[trigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.stemmedMap[trigram_string][vidResponse]

    # for stem_string in queryList:
    #     if stem_string in characterModel.stemmedMap.keys():
    #         for vidResponse in characterModel.stemmedMap[stem_string]:
    #             if vidResponse not in responses.keys():
    #                 responses[vidResponse] = characterModel.stemmedMap[stem_string][vidResponse]
    #             elif vidResponse in responses.keys():
    #                 responses[vidResponse] += characterModel.stemmedMap[stem_string][vidResponse]

    return responses


def lemma_intersection_match_English(query, characterModel, test_par, logger):
    queryList = [lemmatizer.lemmatize(tmp.strip(', " ?.!)')) for tmp in query.split()]

    responses = {}
    queryLen = len(queryList)

    for i in range(queryLen):

        if test_par.unigram == True:

            unigram_string = lemmatized_query[i]
            if unigram_string in avatarModel.lemmatizedMap.keys() and unigram_string not in tokens_used:
                tokens_used.append(unigram_string)

                for obj_videoID in avatarModel.lemmatizedMap[unigram_string]:
                    if obj_videoID not in responses.keys():
                        responses[obj_videoID] = avatarModel.lemmatizedMap[unigram_string][obj_videoID]
                    else:
                        responses[obj_videoID] += avatarModel.lemmatizedMap[unigram_string][obj_videoID]

                    if obj_videoID not in logger.keys():
                        logger[obj_videoID] = {}
                        logger[obj_videoID][unigram_string] = avatarModel.lemmatizedMap[unigram_string][obj_videoID]
                    else:
                        if unigram_string in logger[obj_videoID]:
                            logger[obj_videoID][unigram_string] += avatarModel.lemmatizedMap[unigram_string][obj_videoID]
                        else:
                            logger[obj_videoID][unigram_string] = avatarModel.lemmatizedMap[unigram_string][obj_videoID]

        if test_par.bigram == True:
            if i < queryLen - 2:
                bigram_string = queryList[i] + "_" + queryList[i + 1]
                if bigram_string in characterModel.lemmatizedMap.keys():
                    for vidResponse in characterModel.lemmatizedMap[bigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.lemmatizedMap[bigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.lemmatizedMap[bigram_string][vidResponse]

        if test_par.trigram == True:
            if i < queryLen - 3:
                trigram_string = queryList[i] + "_" + queryList[i + 1] + "_" + queryList[i + 2]
                if trigram_string in characterModel.lemmatizedMap.keys():
                    for vidResponse in characterModel.lemmatizedMap[trigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.lemmatizedMap[trigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.lemmatizedMap[trigram_string][vidResponse]

    # for lemma_string in queryList:
    #     if lemma_string in characterModel.lemmatizedMap.keys():
    #         for vidResponse in characterModel.lemmatizedMap[lemma_string]:
    #             if vidResponse not in responses.keys():
    #                 responses[vidResponse] = characterModel.lemmatizedMap[lemma_string][vidResponse]
    #             elif vidResponse in responses.keys():
    #                 responses[vidResponse] += characterModel.lemmatizedMap[lemma_string][vidResponse]

    return responses


def direct_intersection_match_Arabic(query, characterModel, test_par, logger):
    queryList = [tmp.strip('،!؟."') for tmp in query.split()]
    # queryList.encode('utf-8')

    responses = {}
    queryLen = len(queryList)

    for i in range(queryLen):

        if test_par.unigram == True:

            unigram_string = queryList[i]
            if unigram_string in avatarModel.wordMap.keys() and unigram_string not in tokens_used:
                tokens_used.append(unigram_string)
                for obj_videoID in avatarModel.wordMap[unigram_string]:
                    if obj_videoID not in responses.keys():
                        responses[obj_videoID] = avatarModel.wordMap[unigram_string][obj_videoID]
                    else:
                        responses[obj_videoID] += avatarModel.wordMap[unigram_string][obj_videoID]

                    if obj_videoID not in logger.keys():
                        logger[obj_videoID] = {}
                        logger[obj_videoID][unigram_string] = avatarModel.wordMap[unigram_string][obj_videoID]
                    else:
                        if unigram_string in logger[obj_videoID]:
                            logger[obj_videoID][unigram_string] += avatarModel.wordMap[unigram_string][obj_videoID]
                        else:
                            logger[obj_videoID][unigram_string] = avatarModel.wordMap[unigram_string][obj_videoID]

        if test_par.bigram == True:
            if i < queryLen - 2:
                bigram_string = queryList[i] + "_" + queryList[i + 1]
                if bigram_string in characterModel.wordMap.keys():  # and direct_string not in stop_words:
                    for vidResponse in characterModel.wordMap[bigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.wordMap[bigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.wordMap[bigram_string][vidResponse]

        if test_par.trigram == True:
            if i < queryLen - 3:
                trigram_string = queryList[i] + "_" + queryList[i + 1] + "_" + queryList[i + 2]
                if trigram_string in characterModel.wordMap.keys():  # and direct_string not in stop_words:
                    for vidResponse in characterModel.wordMap[trigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.wordMap[trigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.wordMap[trigram_string][vidResponse]

            '''		
            if(characterModel.objectMap[vidResponse].answerLength):
                recall = responses[vidResponse]/(characterModel.objectMap[vidResponse].questionLength)
                precision= responses[vidResponse]/(characterModel.objectMap[vidResponse].questionLength+characterModel.objectMap[vidResponse].answerLength)
                #f-score
                responses[vidResponse]= responses[vidResponse]/((recall+precision)/2)
            '''

    return responses


def stem_intersection_match_Arabic(query, characterModel, test_par, logger):
    # StarMorphModules.read_config("config_stem.xml")
    # StarMorphModules.initialize_from_file("almor-s31.db","analyze")

    # print("Finding stem Intersection in Arabic")
    queryList = query.strip('؟!،" ً').split()
    responses = {}
    stemmed_query = []
    queryLen = len(queryList)

    for word in queryList:
        analysis = StarMorphModules.analyze_word(word, False)

        stemmed_query.append(analysis[0].split()[1].replace("stem:", "").split('d', 1)[0])

    for i in range(queryLen):

        if test_par.unigram == True:
        unigram_string = stemmed_query[i]

        if unigram_string in avatarModel.stemmedMap.keys() and unigram_string not in tokens_used:
            tokens_used.append(unigram_string)
            for obj_videoID in avatarModel.stemmedMap[unigram_string]:
                if obj_videoID not in responses.keys():
                    responses[obj_videoID] = avatarModel.stemmedMap[unigram_string][obj_videoID]
                else:
                    responses[obj_videoID] += avatarModel.stemmedMap[unigram_string][obj_videoID]

                if obj_videoID not in logger.keys():
                    logger[obj_videoID] = {}
                    logger[obj_videoID][unigram_string] = avatarModel.stemmedMap[unigram_string][obj_videoID]
                else:
                    if unigram_string in logger[obj_videoID]:
                        logger[obj_videoID][unigram_string] += avatarModel.stemmedMap[unigram_string][obj_videoID]
                    else:
                        logger[obj_videoID][unigram_string] = avatarModel.stemmedMap[unigram_string][obj_videoID]

        if test_par.bigram == True:
            if i < queryLen - 2:
                bigram_string = stemmed_query[i] + "_" + stemmed_query[i + 1]
                if bigram_string in characterModel.stemmedMap.keys():  # and direct_string not in stop_words:
                    for vidResponse in characterModel.stemmedMap[bigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.stemmedMap[bigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.stemmedMap[bigram_string][vidResponse]

        if test_par.trigram == True:
            if i < queryLen - 3:
                trigram_string = stemmed_query[i] + "_" + stemmed_query[i + 1] + "_" + stemmed_query[i + 2]
                if trigram_string in characterModel.stemmedMap.keys():  # and direct_string not in stop_words:
                    for vidResponse in characterModel.stemmedMap[trigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.stemmedMap[trigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.stemmedMap[trigram_string][vidResponse]
    # for stem_string in stemmed_query:
    #     if stem_string in characterModel.stemmedMap.keys():
    #         for vidResponse in characterModel.stemmedMap[stem_string]:
    #             if vidResponse not in responses.keys():
    #                 responses[vidResponse] = 1
    #             elif vidResponse in responses.keys():
    #                 responses[vidResponse] += 1

    return responses


def lemma_intersection_match_Arabic(query, characterModel, test_par, logger):
    # print("Finding lemma Intersection in Arabic")
    queryList = query.strip('؟!.،" ً').split()
    # queryList.encode('utf-8')

    responses = {}
    queryLen = len(queryList)

    lemmatized_query = []
    for word in queryList:
        # print(word)
        analysis = StarMorphModules.analyze_word(word, False)
        lemma = analysis[0].split()[0].replace("lex:", "").split('_', 1)[0]
        lemma = re.sub(r'[^\u0621-\u064A]', '', lemma, flags=re.UNICODE)
        lemmatized_query.append(lemma)

    for i in range(queryLen):
        if test_par.unigram == True:
            unigram_string = lemmatized_query[i]
            if unigram_string in avatarModel.lemmatizedMap.keys() and unigram_string not in tokens_used:
                tokens_used.append(unigram_string)

                for obj_videoID in avatarModel.lemmatizedMap[unigram_string]:
                    if obj_videoID not in responses.keys():
                        responses[obj_videoID] = avatarModel.lemmatizedMap[unigram_string][obj_videoID]
                    else:
                        responses[obj_videoID] += avatarModel.lemmatizedMap[unigram_string][obj_videoID]

                    if obj_videoID not in logger.keys():
                        logger[obj_videoID] = {}
                        logger[obj_videoID][unigram_string] = avatarModel.lemmatizedMap[unigram_string][obj_videoID]
                    else:
                        if unigram_string in logger[obj_videoID]:
                            logger[obj_videoID][unigram_string] += avatarModel.lemmatizedMap[unigram_string][obj_videoID]
                        else:
                            logger[obj_videoID][unigram_string] = avatarModel.lemmatizedMap[unigram_string][obj_videoID]

        if test_par.bigram == True:
            if i < queryLen - 2:
                bigram_string = lemmatized_query[i] + "_" + lemmatized_query[i + 1]
                if bigram_string in characterModel.lemmatizedMap.keys():  # and direct_string not in stop_words:
                    for vidResponse in characterModel.lemmatizedMap[bigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.lemmatizedMap[bigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.lemmatizedMap[bigram_string][vidResponse]

        if test_par.trigram == True:
            if i < queryLen - 3:
                trigram_string = lemmatized_query[i] + "_" + lemmatized_query[i + 1] + "_" + lemmatized_query[i + 2]
                if trigram_string in characterModel.lemmatizedMap.keys():  # and direct_string not in stop_words:
                    for vidResponse in characterModel.lemmatizedMap[trigram_string]:
                        if vidResponse not in responses.keys():
                            responses[vidResponse] = characterModel.lemmatizedMap[trigram_string][vidResponse]
                        elif vidResponse in responses.keys():
                            responses[vidResponse] += characterModel.lemmatizedMap[trigram_string][vidResponse]

    # for lemma_string in lemmatized_query:
    #     if lemma_string in characterModel.lemmatizedMap.keys():
    #         for vidResponse in characterModel.lemmatizedMap[lemma_string]:
    #             if vidResponse not in responses.keys():
    #                 responses[vidResponse] = 1
    #             elif vidResponse in responses.keys():
    #                 responses[vidResponse] += 1

    return responses


def calculateTFIDF(avatarModel, test_par):
    # #are we using each question as a "doc" or each avatar model?

    # totalDocs = len(avatarModel.objectMap)

    # #tf: term frequency
    # tf= doc.words.count(token) / len(doc.words)

    # #number of docs containing the token
    # n_containing= sum(1 for doc in doclist if token in doc.words)

    # #idf: inverse document frequency
    # idf= math.log(len(doclist) / (1 + n_containing(token, doclist)))

    # #tfifd
    # tfidf= tf * idf
    # return tfidf

    for avatar in avatarModel:
        totalDocs = len(avatarModel[avatar].objectMap)
        print("Total Docs: ", totalDocs)
        for lemma in avatarModel[avatar].lemmatizedMap.keys():
            idf = totalDocs / len(avatarModel[avatar].lemmatizedMap[lemma])
            for doc in avatarModel[avatar].lemmatizedMap[lemma].keys():
                tf = avatarModel[avatar].lemmatizedMap[lemma][doc]
                tfidf = tf * idf
                #avatarModel[avatar].lemmatizedMap[lemma][doc] = tfidf
                #print("lemma tfidf" + " " + lemma, avatarModel[avatar].lemmatizedMap[lemma][doc])

        # idf: inverse document frequency
        # idf= math.log(len(doclist) / (1 + n_containing(token, doclist)))
        # totaldocs/number of docs the word appears in (don't use the log because it's not a large number of documents)
        # tfifd
        # tfidf= tf * idf

        for stem in avatarModel[avatar].stemmedMap.keys():
            idf = totalDocs / len(avatarModel[avatar].stemmedMap[stem])
            for doc in avatarModel[avatar].stemmedMap[stem].keys():
                tf = avatarModel[avatar].stemmedMap[stem][doc]
                tfidf = tf * idf
                #avatarModel[avatar].stemmedMap[stem][doc] = tfidf

        for word in avatarModel[avatar].wordMap.keys():
            idf = totalDocs / len(avatarModel[avatar].wordMap[word])
            for doc in avatarModel[avatar].wordMap[word].keys():
                tf = avatarModel[avatar].wordMap[word][doc]
                tfidf = tf * idf
                #avatarModel[avatar].wordMap[word][doc] = tfidf

    #print("avatar dict", avatarModel['margarita'].wordMap["hello"][])
   

    #return avatarModel


def rankAnswers(query, videoResponses, currentSession, characterModel):
     query_len = len(query.split())
    allowed=1
    rep=0


    # each repition is a given a weight of 2 e.g if a video has been played once 2 points will be subtracted from its matching score

    # for each possible answer, checks if it has been played it already, and subtract points from its score if has been played already.
    for res in videoResponses.keys():
        videoObjLen = avatarModel.objectMap[res].answerLength
        # precision = videoResponses[res] / videoObjLen
        # recall = videoResponses[res] / query_len
        # f_score = (precision + recall) / 2
        pref_frequency= avatarModel.objectMap[res].frequency
        #print("frequency", pref_frequency)
        
        # if (videoObjLen >int(av_length)):
        #     videoResponses[res] = videoResponses[res]/ videoObjLen
        
        if (pref_frequency=='"never"'):
            #print("yes never")
            allowed=0
        elif(pref_frequency=='"multiple"' or pref_frequency=='"once"'):
            #print("multiple or once")
            allowed=1


        if res in currentSession.repetitions.keys():
            #print("repeats", currentSession.repetitions[res])
            if (pref_frequency=='"multiple"'):
                #print("multiple")
                allowed=1
            elif(pref_frequency=='"once"'):
                if currentSession.repetitions[res]>1:
                    allowed=0
                    print("once done")
                else:
                    allowed=1
                    print("once allowed")
            elif (pref_frequency=='"never"'):
                allowed=0
                #print("never")
            
            rep= currentSession.repetitions[res]

        #print("before",  videoResponses[res])
        #print("allowed", allowed)
        videoResponses[res]=(videoResponses[res]*(1-rep/(total_iterations+1)))*allowed
        #print("after", videoResponses[res])    

    #print("responses", videoResponses)
    ranked_list = sorted(videoResponses, key=lambda i: videoResponses[i], reverse=True)
    #print("ranked list", ranked_list)
    #print("video playing:", ranked_list[0])
    return ranked_list

def findResponse(query, characterModel, currentSession, test_par):

    currentTime = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

    language = currentSession.language
    themax = 0
    best_responses = {}
    stem_match_responses = {}
    lemma_match_responses = {}
    direct_match_responses = {}
    key_repetitions= {}
    logger = {}
    counter=0

    if language == "English":
        f = open('english_log.tsv', 'a', encoding='utf-8')
    else:
        f = open('arabic_log.tsv', 'a', encoding='utf-8')

    query = query.lower().strip(',?.")!')

    if language == "English":
        # different modes of matching
        stem_match_responses = stem_intersection_match_English(query, characterModel, test_par, logger)
        lemma_match_responses = lemma_intersection_match_English(query, characterModel, test_par, logger)
        direct_match_responses = direct_intersection_match_English(query, characterModel, test_par, logger)

    elif language == "Arabic":
        stem_match__responses = stem_intersection_match_Arabic(query, characterModel, test_par, logger)
        lemma_match_responses = lemma_intersection_match_Arabic(query, characterModel, test_par, logger)
        direct_match_responses = direct_intersection_match_Arabic(query, characterModel, test_par, logger)
    else:
        print("language not recognised")
        return

    for key in stem_match_responses.keys():
        if key not in key_repetitions.keys():
            key_repetitions[key]=1
        else:
            key_repetitions[key]+=1
        if key not in best_responses.keys():
            best_responses[key] = stem_match_responses[key]
            best_responses[key]= copy.deepcopy(stem_match_responses[key])
            #print("value", best_responses[key])
           
        else:
            best_responses[key] += copy.deepcopy(stem_match_responses[key])
            

    for key in lemma_match_responses.keys():
        if key not in key_repetitions.keys():
            key_repetitions[key]=1
        else:
            key_repetitions[key]+=1
        if key not in best_responses.keys():
            best_responses[key] = copy.deepcopy(lemma_match_responses[key])
          
        else:
            best_responses[key] += copy.deepcopy(lemma_match_responses[key])
            
            
            

    for key in direct_match_responses.keys():
        if key not in key_repetitions.keys():
            key_repetitions[key]=1
        else:
            key_repetitions[key]+=1
        if key not in best_responses.keys():
            best_responses[key] = copy.deepcopy(direct_match_responses[key])
           
        else:
            best_responses[key] += copy.deepcopy(direct_match_responses[key])
           

    for key in best_responses.keys():
       #print("before", best_responses[key] )
       #print("repetitions", key_repetitions[key])
       best_responses[key]= best_responses[key]/key_repetitions[key]
       #print("after", best_responses[key])
    
    #print("best responses", best_responses)
            
           

   
    # if the responses are empty, play "I can't answer that response"
   
    if bool(best_responses) == False:
        noAnswerList= avatarModel.noAnswer.keys()
        final_answer= random.choice(list(noAnswerList))
      


    else:
       
        ranked_responses = rankAnswers(query, best_responses, currentSession, avatarModel, counter)
        #print("final responses", ranked_responses)
        final_answer = ranked_responses[0]

        # if len(ranked_responses) > 2:
        #     second_response = ranked_responses[1]
        #     third_response = ranked_responses[2]
        #     log_string = currentTime + "\t" + currentSession.currentAvatar + "\t" + query + "\t" + avatarModel.objectMap[final_answer].answer + "\t" + str(best_responses[final_answer]) + "\t" + str(logger[final_answer]) +  "\t" + avatarModel.objectMap[second_response].answer + "\t" + str(best_responses[second_response]) + "\t" + str(logger[second_response]) +  "\t" + avatarModel.objectMap[third_response].answer + "\t" + str(best_responses[third_response]) + "\t" + str(logger[third_response]) + "\n"

        # elif len(ranked_responses) == 2:
        #     second_response = ranked_responses[1]
        #     log_string = currentTime + "\t" + currentSession.currentAvatar + "\t" + query + "\t" + avatarModel.objectMap[final_answer].answer + "\t" + str(best_responses[final_answer]) + "\t" + str(logger[final_answer]) +  "\t" + avatarModel.objectMap[second_response].answer + "\t" + str(best_responses[second_response]) + "\t" + str(logger[second_response]) +  "\t\t\t\n"

        # else:
        #     log_string = currentTime + "\t" + currentSession.currentAvatar + "\t" + query + "\t" + avatarModel.objectMap[final_answer].answer + "\t" + str(best_responses[final_answer]) + "\t" + str(logger[final_answer]) +  "\t\t\t\t\t\t\n"


        # #print(log_string)
        # f.write(log_string)
        # f.close()
        if final_answer in currentSession.repetitions.keys():
            currentSession.repetitions[final_answer] += 1
        else:
            currentSession.repetitions[final_answer] = 1


    return avatarModel.objectMap[final_answer]


def determineAvatar(query, currentSession):
    if currentSession.currentAvatar == "":
        currentSession = session("margarita", currentSession.language)

    # Changes the avatar

    if query == "toya toya can i talk to margarita":
        currentSession = session("margarita", currentSession.language)

    if query == "toya toya can i talk to rashid":
        currentSession = session("rashid", currentSession.language)

    if query == "toya toya can i talk to katarina":
        print("you are switching to katarina")
        currentSession = session("katarina", currentSession.language)

    if query == "toya toya can i talk to gabriela":
        currentSession = session("gabriela", currentSession.language)

    if query == "toya toya can i talk to gabriella":
        currentSession = session("gabriela", currentSession.language)

    if query == "toya toya can i talk to someone else":
        print("you are switching to gabriela")
        currentSession = session("gabriela", currentSession.language)

    return currentSession


# the player calls the following functions for greetings and silentVideos, using calls such as dialogue-manager3.sayHi(avatarl[avatar])

def silentVideos(corpus):
    return corpus["silences"]


def sayHi(corpus):
    return corpus["greetings"][0]


def sayBye(corpus):
    return corpus["greetings"][-1]


def create_new_session(avatar, language):
    print("creating a new session for " + avatar + " in " + language)

    if language == "English":
        f = open('english_log.tsv', 'a', encoding='utf-8')
    else:
        f = open('arabic_log.tsv', 'a', encoding='utf-8')
    log_string = "\t\t\t\t\t\t\t\t\t\t\n"
    f.write(log_string)
    f.close()
    return session(avatar, language)


def main():
    return


if __name__ == "__main__":



    for synset in wn.synsets("family"):
        for lemma in synset.lemmas():
                print(lemma.name())
    """ This is executed when run from the command line """
    main()
