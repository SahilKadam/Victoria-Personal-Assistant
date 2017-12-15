import speech_recognition as sr
import pyttsx
from stanfordcorenlp import StanfordCoreNLP
from nltk.tree import ParentedTree
from nltk.corpus import stopwords
from neo4jrestclient.client import GraphDatabase
from neo4jrestclient import client
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer

# This function converts the speech i.e. voice commands to text format.
def speechToTextConverter(): 
	# Record Audio
	r = sr.Recognizer()
	with sr.Microphone() as source:
		print("Listening!")
		audio = r.listen(source)
	 
	# Speech recognition using Google Speech Recognition
	try:
		# for testing purposes, we're just using the default API key
		# to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
		# instead of `r.recognize_google(audio)`
		text = r.recognize_google(audio)
		return (text)
	except sr.UnknownValueError:
		print("Google Speech Recognition could not understand audio")
		return (-1)
	except sr.RequestError as e:
		print("Could not request results from Google Speech Recognition service; {0}".format(e))
		return (-1)

# This function converts a given text to speech.		
def textToSpeech(text):
	engine = pyttsx.init()
	engine.setProperty('voice', 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_EN-US_ZIRA_11.0')
	engine.setProperty('rate', 140)
	engine.say(text)
	engine.runAndWait()

# This function updates the Pos_tags.
# ex: Donald Trump is one word. But in Standford core NLP,
# its gives Donald and Trump as two different nouns.
# This function combines the two nouns into one.	
def updatePosTagsAnsNer(pos_tags):
	updated_pos = [[pos_tags[0][0], pos_tags[0][1]]]

	nnpList = ['NNP', 'NNPS']

	for i in range(1,len(pos_tags)):
		if pos_tags[i][1] in nnpList and pos_tags[i-1][1] in nnpList:
			updated_pos.pop()
			updated_pos.append([pos_tags[i-1][0] + " " + pos_tags[i][0], pos_tags[i][1]])
		else:
			updated_pos.append([pos_tags[i][0], pos_tags[i][1]])
			
	return (updated_pos)

# This function is used to remove stop words.	
def removeStopWords(sentence, stopwords):
	sentence = sentence.split()
	cleanSentence = [i for i in sentence if i not in stopwords]
	cleanSentence = " ".join(cleanSentence)
	return (cleanSentence)

# This function is used to insert new data into the graph database.	
def create(db, first, relationship, last):
	nnp = db.labels.create("NNP")
	node_first = db.nodes.create(name=first.lower())
	node_last = db.nodes.create(name=last.lower())
	nnp.add(node_first, node_last)
	node_first.relationships.create(relationship.lower(), node_last)

# This function is used to filter data from the Graph Database.	
def query(db, relationship, last, sentence, chatbot):
	q = 'MATCH (p)<-[: ' + relationship.lower() + ']-(n) WHERE p.name = "' + last.lower() + '" RETURN n.name'
	results = db.query(q, returns=(str))
	if (len(results)):
		sentence = sentence.split()
		sentence[0] = results[0][0]
		sentence = " ".join(sentence)
		return (sentence)
	else:
		return(chatbot.get_response(sentence))

# This function is called when Victoria is woken up,
# by saying "Hey Victoria" or "Okay Victoria".		
def take_action(sentence, chatbot):
	nlp = StanfordCoreNLP(r'C:\ANLP\Project\stanford-corenlp-full-2017-06-09')
	stopWords = set(stopwords.words('english'))
	parsedSentence = nlp.parse(sentence)
	parsetree = ParentedTree.fromstring(parsedSentence)
	cleanSentence = sentence
	cleanSentence = removeStopWords(sentence, stopWords)
	if (len(cleanSentence) == 0):
		textToSpeech((chatbot.get_response(sentence)))
		return
		
	pos_tags = nlp.pos_tag(cleanSentence)
	updated_pos = updatePosTagsAnsNer(pos_tags)
	db = GraphDatabase("http://localhost:7474")


	if parsetree[0].label() == "SINV" or parsetree[0].label() == "SBARQ":
		if (len(updated_pos) != 2):
			textToSpeech((chatbot.get_response(sentence)))
			return
		NNP_pos = [i for i in updated_pos if i[1] in ["NN", "NNP", "NNPS"]]
		spokenText = query(db, updated_pos[0][0], updated_pos[1][0], sentence, chatbot)
	else:
		if (len(updated_pos) != 3):
			textToSpeech((chatbot.get_response(sentence)))
			return
		create(db, updated_pos[0][0], updated_pos[1][0], updated_pos[2][0])
		spokenText = "I have update the database with the new information"
	
	textToSpeech(spokenText)

# This the main method which is called on script initiation.	
def main():
	print "Training Conversation Module. It make take few minutes..."
	print ""
	print ""
	chatbot = ChatBot("Sahil Kadam", trainer='chatterbot.trainers.ChatterBotCorpusTrainer')
	chatbot.train("chatterbot.corpus.english")
	print ""
	print ""
	print "Conversation Module Training completed."
	act_flag = False
	while(True):
		spokenText = speechToTextConverter()
		print "You said: ", spokenText
		if spokenText == -1:
			continue
		if "okay victoria" in spokenText.lower() or "hey victoria" in spokenText.lower():
			textToSpeech((chatbot.get_response("Hello")))
			act_flag = True
		
		if act_flag == True:
			actionText = speechToTextConverter()
			print "You said: ", actionText
			if spokenText == -1:
				continue
			take_action(actionText, chatbot)
			act_flag = False
			
if __name__ == "__main__":
	main()