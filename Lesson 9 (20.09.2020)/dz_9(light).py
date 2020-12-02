# -*- coding: utf-8 -*-
"""DZ-9(Light).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/12OrmMQNmjJsSWqA37EjOK_gCYXR_yQgu
"""

from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import Dense, Flatten, Reshape, Conv2DTranspose, concatenate, Activation, \
MaxPooling2D, Conv2D, BatchNormalization, Input
from tensorflow.keras import backend as K
from tensorflow.keras.optimizers import Adam
from tensorflow.keras import utils
from tensorflow.keras.datasets import mnist, fashion_mnist

import matplotlib.pyplot as plt
from tensorflow.keras.preprocessing import image
from PIL import Image

import numpy as np
import pandas as pd
import time
import os

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from google.colab import drive
drive.mount('/content/drive')

!unzip -q '/content/drive/My Drive/datasets/Лица.zip'

images_dir = 'Лица'
img_height = 112
img_width = 80

# Функция загрузки изображений
def load_images(images_dir, img_height, img_width):
  list_img = []
  for img in os.listdir(images_dir):
    list_img.append(image.img_to_array(image.load_img
                                       (os.path.join(images_dir, img), target_size=(img_height, img_width), color_mode='grayscale')))
  print('OK')
  return np.array(list_img)

cur_time = time.time()
xTrain_img = load_images(images_dir, img_height, img_width)
print ('Время загрузки: ', round(time.time()-cur_time, 2), 'с', sep='')

xTrain_img = xTrain_img/255
xTrain_img.shape

plt.imshow(xTrain_img[np.random.randint(0, xTrain_img.shape[0])].reshape(112, 80), cmap='gray')
plt.show()

# функцию создания базового автокодировщика
def baseAutoencoder(shape=(112, 80, 1)):
    img_input = Input((shape))
    # входные данные передаем на слой двумерной свёртки
    x = Conv2D(32, (3, 3), padding='same', activation='relu')(img_input)
    x = BatchNormalization()(x) 
    x = Conv2D(32, (3, 3), padding='same', activation='relu')(x)
    x = BatchNormalization()(x)
    x = MaxPooling2D()(x)

    # передаем на слой двумерной свёртки
    x = Conv2D(64, (3, 3), padding='same', activation='relu')(x)
    x = BatchNormalization()(x) 
    x = Conv2D(64, (3, 3), padding='same', activation='relu')(x)
    x = BatchNormalization()(x)
    z = MaxPooling2D()(x)
    
    # слой разжимает данные(с 28*20 на 56*40)
    x = Conv2DTranspose(64, (2, 2), strides=(2, 2), padding='same', activation='relu')(z) 
    x = BatchNormalization()(x)
    
    # передаем на слой двумерной свёртки
    x = Conv2D(64, (3, 3), padding='same', activation='relu')(x) 
    x = BatchNormalization()(x)
    x = Conv2D(64, (3, 3), padding='same', activation='relu')(x)
    x = BatchNormalization()(x)
    # Сжатие MaxPooling2D не применяем

    # слой разжимает данные(с 56*40 на 112*80)
    x = Conv2DTranspose(32, (2, 2), strides=(2, 2), padding='same', activation='relu')(x) 
    x = BatchNormalization()(x)
    x = Conv2D(32, (3, 3), padding='same', activation='relu')(x)
    x = BatchNormalization()(x)
    x = Conv2D(32, (3, 3), padding='same', activation='relu')(x)
    x = BatchNormalization()(x)

    # Финальный слой двумерной свертки, выдающий итоговое изображение
    x = Conv2D(1, (3, 3), activation='sigmoid', padding='same')(x)

    # указываем модель, с оригинальным изображением на входе в сеть и сжатым-разжатым на выходе из сети
    model = Model(img_input, x)

    # компилируем модель с оптимайзером Адам и среднеквадратичной ошибкой
    model.compile(optimizer=Adam(lr=0.0001), loss='mean_squared_error') 

    return model

modelAutoFace = baseAutoencoder() # создаем автокодировщик
modelAutoFace.fit(xTrain_img[:4700], xTrain_img[:4700], epochs=150, batch_size=100, validation_data = (xTrain_img[4700:], xTrain_img[4700:]))

# modelAutoFace.save_weights('modelAutoFace.h5') # Сохраняем модель
modelAutoFace.load_weights('modelAutoFace.h5') # Сохраняем модель

# создадим функцию для вывода изображений как картинок
def plotImages(xTrain, pred, shape=(112, 80)): 
  
  n = 7  
  plt.figure(figsize=(10, 4))
  for i in range(n):
      index = np.random.randint(0, pred.shape[0])
      # Показываем картинки из тестового набора
      ax = plt.subplot(2, n, i + 1)
      plt.imshow(xTrain[index].reshape(shape))     
      plt.gray()
      ax.get_xaxis().set_visible(False)
      ax.get_yaxis().set_visible(False)

      # Показываем восстановленные картинки
      ax = plt.subplot(2, n, i + 1 + n)
      plt.imshow(pred[index].reshape(shape))    
      plt.gray()
      ax.get_xaxis().set_visible(False)
      ax.get_yaxis().set_visible(False)
  plt.show()

# создадим функцию среднеквадратичной ошибки
def getMSE(x1, x2): 
  x1 = x1.flatten()
  x2 = x2.flatten()
  delta = x1 - x2
  # и возвращаем сумму квадратов разницы, делённую на длину разницы
  return sum(delta ** 2) / len(delta)

predFace = modelAutoFace.predict(xTrain_img[:100])
predFace = predFace * 255
predFace = predFace.astype('uint8')
plotImages(xTrain_img, predFace)

# Возьмем среднеквадратичные ошибки и выведем их для лиц 
errFace = [getMSE(xTrain_img[i], predFace[i] / 255) for i in range(len(predFace))]
print("Ошибка на Лицах:", errFace[80:])
print("Средняя ошибка на Лицах:", round(sum(errFace[80:]) / len(errFace[80:]), 4))
print("Минимальная ошибка на Лицах:", round(min(errFace),4))

# установим какое-то пороговое значение
bias = 0.004 
isFace = [e < bias for e in errFace[80:]]
print("Лица распознаны, как Лица: ", round(100*sum(isFace) / len(isFace)),"%", sep="")

# создаем 100 картинок шума
noise = np.random.sample((100,112,80,1)) 
print(noise.shape)

# сделаем предикт этих шумовых картинок
predNoise = modelAutoFace.predict(noise[:100]) 
predNoise = predNoise * 255 
predNoise = predNoise.astype('uint8')

# выведем на экран исходные шумовые картинки и восстановленые 
plotImages(noise, predNoise)

# Возьмем среднеквадратичные ошибки и выведем их для Mnist и для шумовых изображений
errN = [getMSE(noise[i], predNoise[i] / 255) for i in range(len(predFace))]
print("Ошибка на Лицах:", errFace[0:20])
print("Ошибка на шуме:", errN[0:20])
print("Средняя ошибка на Лицах:", round(sum(errFace) / len(errFace), 4))
print("Средняя ошибка на шуме:", round(sum(errN) / len(errN), 4))
print("Максимальная ошибка на Лицах:", round(max(errFace),4))
print("Минимальная ошибка на шуме:", round(min(errN),4))

# объявим функцию добавления шума
def addNoise(x, noiseVal): 
  noise = np.random.normal(loc=0.5, scale=0.5, size=x.shape) 
  return np.clip(x + noiseVal * noise, 0., 1.)

# cоздаем зашумленный вариант лиц из xTrain_img
noisedXTrainFace = addNoise(xTrain_img, 0.4)

# выведем на экран исходные лица и зашумленные варианты 
plotImages(xTrain_img, noisedXTrainFace)

# объявляем функцию создания автокодировщика для подавления шума
def denoiseAutoencoder(): 
    img_input = Input((112,80,1))

    # Добавляем четыре сверточных слоя, вместо MaxPooling используем strides
    x = Conv2D(32, (3, 3), strides=2, activation='relu', padding='same')(img_input)
    x = Conv2D(64, (3, 3), strides=2, activation='relu', padding='same')(x)
    x = Conv2D(128, (3, 3), strides=2, activation='relu', padding='same')(x)
    x = Conv2D(256, (3, 3), strides=2, activation='relu', padding='same')(x)
    # сплющиваем в одномерный вектор - размер 7*5*256
    x = Flatten()(x) 
    z = Dense(256, activation='relu')(x)
    # и еще полносвязный слой с переводом в 8960-мерное пространство(7*5*256)
    x = Dense(7*5*256, activation='relu')(z) 
    # меняем размеры - картинка 7*5 , 256 ядер
    x = Reshape((7,5,256))(x) 
    x = Conv2DTranspose(256, (3, 3), strides=2, padding='same')(x) 
    x = Conv2DTranspose(128, (3, 3), strides=2, padding='same')(x) 
    x = Conv2DTranspose(64, (3, 3), strides=2, padding='same')(x) 
    x = Conv2DTranspose(32, (3, 3), strides=2, padding='same')(x) 
    x = Conv2D(1, (3, 3), activation='sigmoid', padding='same')(x)

    # собрали модель с зашумленной картинкой на вход и с очищенной от шума на выход
    model = Model(img_input, x)
    # компилируем модель также, с выбором оптимайзера и среднеквадратичной ошибки
    model.compile(optimizer='adam', loss='mse') 
                  
    return model

modelDenoiseFace = denoiseAutoencoder()
# Подаем на вход зашумленные картинки, а на выход правильные, исходные картинки, и обучаем
modelDenoiseFace.fit(noisedXTrainFace[:4700], xTrain_img[:4700], epochs=80, batch_size=100, 
                     validation_data = (noisedXTrainFace[4700:], xTrain_img[4700:]))

# modelDenoiseFace.save_weights('modelDenoiseFace.h5') # Сохраняем модель
modelDenoiseFace.load_weights('modelDenoiseFace.h5') # Сохраняем модель

# подаем 4тыс зашумленных картинок и делаем предикт
predFaceDenoise = modelDenoiseFace.predict(noisedXTrainFace[:4000]) 
predFaceDenoise = predFaceDenoise * 255 
predFaceDenoise = predFaceDenoise.astype('uint8')

plotImages(noisedXTrainFace, predFaceDenoise) # взглянем как отрабатывает шумоподавление на зашумленных картинках

plotImages(xTrain_img, predFaceDenoise) # взглянем как отрабатывает шумоподавление на лицах

