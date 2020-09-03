# -*- coding: utf-8 -*-
"""Final_WordLevelEngMarNMT.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1jnmZqMPWP1MnLvA151rgTT29rL1NWaZQ
"""

from keras.models import Model
import string
from keras.layers import Input, LSTM, Embedding, Dense
from string import digits
import re 
from sklearn.model_selection import train_test_split #Used to split training and testing data
import pandas as pd #Used for reading CSV File
import numpy as np #For performing Linear Algebra operations

df = pd.read_csv('marathiAndEnglish.csv')

df.head()

#Lower all characters
df['english'] = df['english'].str.lower() 
df['marathi'] = df['marathi'].str.lower()

df.head()

# Remove double and single quotes
df['english'] = df['english'].str.replace("'","", regex=True).replace('"',"", regex=True)
df['marathi'] = df['marathi'].str.replace("'","", regex=True).replace('"',"", regex=True)

df.head()

specialCharacters = {'!','"','#','$','%','&',"'",'(',')','*','+',',','-','.','/',':',';','<','=','>','?','@','[','\\',']','^','_','`','{','|','}','~'}

# Remove all the special characters from the columns
df['english'] = df['english'].apply(lambda x: ''.join(char for char in x if char not in specialCharacters))
df['marathi'] = df['marathi'].apply(lambda x: ''.join(char for char in x if char not in specialCharacters))

df.head()

# Remove all numbers from the columns in English and Marathi
df['english'] = df['english'].str.replace('\d+', '', regex=True)
df['marathi'] = df['marathi'].str.replace('\d+', '', regex=True)
df['marathi'] = df['marathi'].str.replace('२|३|०|८|१|५|७|९|४|६', "", regex=True)
df['english'] = df['english'].str.replace('२|३|०|८|१|५|७|९|४|६', "", regex=True)
df.head()

# Remove extra spaces
df['english'] = df['english'].apply(lambda x: x.strip())
df['marathi'] = df['marathi'].apply(lambda x: x.strip())
df['english'] = df['english'].apply(lambda x: re.sub(" +", " ", x))
df['marathi'] = df['marathi'].apply(lambda x: re.sub(" +", " ", x))
df.head()

# Add start and end tokens to target sequences
df['marathi'] = df['marathi'].apply(lambda x : 'S_ '+ x + ' _E')

allEnglishWords =  list(df['english'].str.split(' ', expand=True).stack().unique())
allMarathiWords = list(df['marathi'].str.split(' ', expand=True).stack().unique())

df.head(5)

english_Word_Max_Length = df['english'].str.split(" ").map(len).max()
english_Word_Max_Length

marathi_Word_Max_Length = df['marathi'].str.split(" ").map(len).max()
marathi_Word_Max_Length

allEnglishWords = sorted(list(allEnglishWords))
allMarathiWords = sorted(list(allMarathiWords))
encoder_tokens_len = len(allEnglishWords)
decoder_tokens_len = len(allMarathiWords) + 1 #Adding 1 for padding

input_token_index = dict([(word, i+1) for i, word in enumerate(allEnglishWords)])
target_token_index = dict([(word, i+1) for i, word in enumerate(allMarathiWords)])

reverse_input_char_index = dict((i, word) for word, i in input_token_index.items())
reverse_target_char_index = dict((i, word) for word, i in target_token_index.items())

X_train, X_test, y_train, y_test = train_test_split(df['english'], df['marathi'], test_size = 0.1,random_state=42) #Train test split. 90% training and 10% testing.

def generate_data_in_batch(X,y,batch_size):
    while True:
        for j in range(0, len(X), batch_size):
            encoderInputData = np.zeros((batch_size, english_Word_Max_Length),dtype='float32')
            decoderInputData = np.zeros((batch_size, marathi_Word_Max_Length),dtype='float32')
            decoder_target_data = np.zeros((batch_size, marathi_Word_Max_Length, decoder_tokens_len),dtype='float32')
            for i, (input_text, target_text) in enumerate(zip(X[j:j+batch_size], y[j:j+batch_size])):
                for t, word in enumerate(input_text.split()):
                    encoderInputData[i, t] = input_token_index[word] # encoder input seq
                for t, word in enumerate(target_text.split()):
                    if t<len(target_text.split())-1: 
                        decoderInputData[i, t] = target_token_index[word] # decoder input seq
                    if t>0: 
                        decoder_target_data[i, t - 1, target_token_index[word]] = 1.
            yield([encoderInputData, decoderInputData], decoder_target_data)



encoder_inputs = Input(shape=(None,))
enc_emb =  Embedding(encoder_tokens_len, 50, mask_zero = True)(encoder_inputs)
encoder_lstm = LSTM(50, return_state=True)
encoder_outputs, state_h, state_c = encoder_lstm(enc_emb)
encoder_states = [state_h, state_c] # We just discard the `encoder_outputs` and only keep the states.

decoder_inputs = Input(shape=(None,)) # Set up the decoder, using `encoder_states` as initial state.
dec_emb_layer = Embedding(decoder_tokens_len, 50, mask_zero = True)
dec_emb = dec_emb_layer(decoder_inputs)
# We set up our decoder to return full output sequences, and to return internal states as well. We don't use the return states in the training model, but we will use them in inference.
decoder_lstm = LSTM(50, return_sequences=True, return_state=True)
decoder_outputs, _, _ = decoder_lstm(dec_emb, initial_state=encoder_states)
decoder_dense = Dense(decoder_tokens_len, activation='softmax')
decoder_outputs = decoder_dense(decoder_outputs)
model = Model([encoder_inputs, decoder_inputs], decoder_outputs)

model.compile(optimizer='rmsprop', loss='categorical_crossentropy', metrics=['accuracy']) #Use accuracy metric



model.fit_generator(generator = generate_data_in_batch(X_train, y_train, batch_size = 128),
                    epochs=250,
                    steps_per_epoch = len(X_train)//128,
                    validation_steps = len(X_test)//128,
                    validation_data = generate_data_in_batch(X_test, y_test, batch_size = 128))

# Commented out IPython magic to ensure Python compatibility.
import matplotlib.pyplot as plt
# %matplotlib inline
plt.plot(range(len(model.history.history['val_loss'])),model.history.history['loss'])
plt.xlabel("epochs")
plt.ylabel("loss")
plt.show()

### Ploting epoch vs accuracy
plt.plot(range(len(model.history.history['acc'])),model.history.history['acc'])
plt.xlabel("epochs")
plt.ylabel("accuracy")
plt.show()

"""# Training is completed. Now let's create test"""

encoder_model = Model(encoder_inputs, encoder_states) # Encode the input sequence to get the "thought vectors"
decoderState_inputs = [Input(shape=(50,)), Input(shape=(50,))]
decoder_outputs2, state_h2, state_c2 = decoder_lstm(dec_emb_layer(decoder_inputs), initial_state=decoderState_inputs)
decoder_model = Model([decoder_inputs] + decoderState_inputs,[decoder_dense(decoder_outputs2)] + [state_h2, state_c2])

def decode_sequence(input_seq):
    states_value = encoder_model.predict(input_seq) # Encode the input as state vectors.
    target_seq = np.zeros((1,1)) # Generate empty target sequence of length 1.
    target_seq[0, 0] = target_token_index['S_'] # Populate the first character of target sequence with the start character.

    stop = False
    decoded_sentence = ''
    while not stop:
        output_tokens, h, c = decoder_model.predict([target_seq] + states_value)

        # Sample a token
        sampled_char = reverse_target_char_index[np.argmax(output_tokens[0, -1, :])]
        
        if (sampled_char == '_E' or len(decoded_sentence+' '+sampled_char) > 50):
            stop = True

        # Update the target sequence (of length 1).
        target_seq = np.zeros((1,1))
        target_seq[0, 0] = np.argmax(output_tokens[0, -1, :])
        states_value = [h, c]
    return decoded_sentence+' '+sampled_char

"""### Evaluation on Train Dataset"""

data_Valid = generate_data_in_batch(X_train, y_train, batch_size = 1)

(input_seq, actual_output), _ = next(data_Valid)
row=0
print('Input English sentence:', X_train[row:row+1].values[0])
print('Predicted sentence:', decode_sequence(input_seq)[:-4])
print('Actual sentence:', y_train[row:row+1].values[0][6:-4])

"""# Evaluation on Testing Set"""

val_gen =  generate_data_in_batch(X_test, y_test, batch_size = 1)
row=2

(input_seq, actual_output), _ = next(val_gen)
decoded_sentence = decode_sequence(input_seq)
print('Input English sentence:', X_test[row:row+1].values[0])
print('Actual Marathi Translation:', y_test[row:row+1].values[0][6:-4])
print('Predicted Marathi Translation:', decoded_sentence[:-4])

import nltk.translate.bleu_score as bleu
print("BLEU score is", bleu.sentence_bleu(y_test[row:row+1].values[0][6:-4],decoded_sentence[:-4]))

