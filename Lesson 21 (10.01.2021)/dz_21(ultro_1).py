# -*- coding: utf-8 -*-
"""DZ-21(Ultro-1).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1BR_rq0BRCQcF03hURabumrNlvBsOmywr
"""

!pip uninstall -y keras tensorflow fancyimpute
!pip install keras==2.2.5 tensorflow-gpu==1.13.1 findspark sparkdl \
    tensorframes kafka-python tensorflowonspark

!pip install sparkdl

# Устанавливаем необходимые пакеты
!apt-get update
!apt-get install openjdk-8-jdk-headless
!wget http://mirror.klaus-uwe.me/apache/spark/spark-2.4.7/spark-2.4.7-bin-hadoop2.7.tgz
!tar xf spark-2.4.7-bin-hadoop2.7.tgz
!update-alternatives --set java /usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java
!java -version

!ls /usr/lib/jvm/java-8-openjdk-amd64
!pip install -q findspark

# Устанавливаем CUDA 9.0
!wget https://developer.nvidia.com/compute/cuda/9.0/Prod/local_installers/cuda-repo-ubuntu1604-9-0-local_9.0.176-1_amd64-deb
!dpkg -i cuda-repo-ubuntu1604-9-0-local_9.0.176-1_amd64-deb
!apt-key add /var/cuda-repo-9-0-local/7fa2af80.pub
!apt-get update
!apt-get install cuda=9.0.176-1

import os
# Задаем окружение
# Указываем переменные окружения для findspark
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-8-openjdk-amd64"
os.environ["SPARK_HOME"] = "spark-2.4.7-bin-hadoop2.7"

# Инциализируем pyspark из директории с библиотекой
import findspark
findspark.init()

# Запускаем Spark-сессию
from pyspark.sql import SparkSession
spark = SparkSession.builder.master('local[*]').config("spark.driver.memory", "16g").getOrCreate()

# Подгружаем google-диск
from google.colab import drive
drive.mount('/content/drive/')

# Загружаем ключ API
from google.colab import files
files.upload()

# # Загружаем 
# !mkdir -p ~/.kaggle
# !cp kaggle.json ~/.kaggle/
# # Изменим разрешение
# !chmod 600 ~/.kaggle/kaggle.json
# # Загрузим датасет с Kaggle
# !kaggle competitions download -c dogs-vs-cats

# 
# !unzip -q train.zip -d .
# !unzip -q test1.zip -d .

!ls '/content/'

# Распарсим обучающую выборку на категории
filenames = os.listdir('/content/train/')
categories = []
for filename in filenames:
    category = filename.split('.')[0]
    if category == 'dog':
        categories.append(str(1))
    else:
        categories.append(str(0))

# Загружаем пандас для создания таблицы
import pandas as pd

df = pd.DataFrame({
    'filename': filenames,
    'category': categories
})

display(df)

# Выведем случайное изображение
import tensorflow as tf
import keras
import random
import matplotlib.pyplot as plt
from keras.preprocessing.image import load_img

sample = random.choice(filenames)
image = load_img("/content/train/" + sample)
plt.imshow(image)

# Преобразуем его в датафрейм spark
data = spark.createDataFrame(df)
data.show()

data.printSchema()

# Проверим статистику
data.describe(["filename","category"]).show()

from keras.applications import InceptionV3

model = InceptionV3(weights="imagenet")
model.save('model-full.h5')

from keras.applications.inception_v3 import preprocess_input
from keras.preprocessing.image import img_to_array, load_img
import numpy as np
from pyspark.sql.types import StringType
from sparkdl import KerasImageFileTransformer

def loadAndPreprocessKerasInceptionV3(data):
    image = img_to_array(load_img(data, target_size=(299, 299)))
    image = np.expand_dims(image, axis=0)
    return preprocess_input(image)

transformer = KerasImageFileTransformer(inputCol="filename", outputCol="category",
                                        modelFile='model-full.h5',
                                        imageLoader=loadAndPreprocessKerasInceptionV3,
                                        outputMode="vector")
transformer

fs = !ls content/train/*.jpg
uri_df = spark.createDataFrame(fs, StringType()).toDF("filename")
keras_pred_df = transformer.transform(uri_df)

from keras.models import Sequential
from keras.layers import Dense
import numpy as np
from pyspark.sql.types import StructType, StructField, ArrayType, FloatType

num_features = 10
num_examples = 100
input_data = [{"features" : np.random.randn(num_features).astype(float).tolist()} for i in range(num_examples)]
schema = StructType([ StructField("features", ArrayType(FloatType()), True)])
input_df = spark.createDataFrame(input_data, schema)


model = Sequential()
model.add(Dense(units=20, input_shape=[num_features], activation='relu'))
model.add(Dense(units=1, activation='sigmoid'))
model_path = "simple-binary-classification"
model.save('model_path')


transformer = KerasImageFileTransformer(inputCol="features", outputCol="category",
                                        modelFile='model_path',
                                        imageLoader=loadAndPreprocessKerasInceptionV3,
                                        outputMode="vector")
final_df = transformer.transform(input_df)