# -*- coding: utf-8 -*-
"""DZ_11(PRO).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1p9YnFyglyD5ycYhXnZkc7RRvmieXYGbN
"""

import scipy

from tensorflow.python.keras.layers import Input, Dense, Reshape, Flatten, Dropout, Concatenate, LeakyReLU
from tensorflow.python.keras.layers import BatchNormalization, Add, add
from tensorflow.python.keras.layers import UpSampling2D, Conv2D
from tensorflow.python.keras.applications import vgg19
#from tensorflow.python.keras.utils import plot_model
from keras.utils import plot_model
#from tensorflow.python.keras.preprocessing.image import img_to_array, load_img
from keras.preprocessing.image import img_to_array, load_img
#from tensorflow.python.keras.models import Sequential, Model
from keras.models import Sequential, Model
#from tensorflow.python.keras.optimizers import Adam
from keras.optimizers import Adam
import matplotlib.pyplot as plt
import numpy as np
import os
import tensorflow.python.keras.backend as K
from tqdm import tqdm

from tensorflow.python.platform.tf_logging import set_verbosity, FATAL
#отключаем отображение некритических предупреждений
set_verbosity(FATAL)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = '0'

#подключаем google drive, чтобы достать из него необходимый dataset
from google.colab import drive 
drive.mount('/content/drive')

img_shape = (256, 384, 3) #размер изображения
height = img_shape[0]
width = img_shape[1]

!unzip -q '/content/drive/My Drive/datasets/images/Самолеты.zip'

!ls '/content/База/Airplane/'

PATH = '/content/База/Airplane/'
mask = '/content/База/Segment/'
imgs = [] 
for image in sorted(os.listdir(PATH)): #проходим по каждому файлу, получив список файлов в папке 
  print(image)
  imgs.append(img_to_array(load_img(PATH + image, target_size=(height, width)))) #загружаем файл, устанавливаем нужный размер и сохраняем в оперативную память, как массив numpy
imgs = np.stack(imgs).astype('uint8') #сохраняем итоговый массив изображений

masks = []
for image in sorted(os.listdir(mask)): #проходим по каждому файлу, получив список файлов в папке 
  masks.append(img_to_array(load_img(mask + image, target_size=(height, width)))) #загружаем файл, устанавливаем нужный размер и сохраняем в оперативную память, как массив numpy
masks = np.stack(masks).astype('uint8') #сохраняем итоговый массив масок

def build_generator():
    gf = 64
    def conv2d(layer_input, filters, f_size=4, bn=True): 
        d = Conv2D(filters, kernel_size=f_size, strides=2, padding='same')(layer_input)
        d = LeakyReLU(alpha=0.2)(d)
        if bn:
            d = BatchNormalization(momentum=0.8)(d)
        return d

    def deconv2d(layer_input, skip_input, filters, f_size=4, dropout_rate=0): 
        u = UpSampling2D(size=2)(layer_input) 
        u = Conv2D(filters, kernel_size=f_size, strides=1, padding='same', activation='relu')(u)
        if dropout_rate:
            u = Dropout(dropout_rate)(u)
        u = BatchNormalization(momentum=0.8)(u)
        u = Concatenate()([u, skip_input])
        return u
    
    d0 = Input(shape=img_shape, name="condition")
    d1 = conv2d(d0, gf, bn=False)
    d2 = conv2d(d1, gf*2)
    d3 = conv2d(d2, gf*4) 
    d4 = conv2d(d3, gf*8)
    d5 = conv2d(d4, gf*8)
    d6 = conv2d(d5, gf*8)
    d7 = conv2d(d6, gf*8)

    u1 = deconv2d(d7, d6, gf*8)
    u2 = deconv2d(u1, d5, gf*8) 
    u3 = deconv2d(u2, d4, gf*8) 
    u4 = deconv2d(u3, d3, gf*4) 
    u5 = deconv2d(u4, d2, gf*2)
    u6 = deconv2d(u5, d1, gf)

    u7 = UpSampling2D(size=2)(u6)
    output_img = Conv2D(3, kernel_size=4, strides=1, padding='same', activation='tanh', name='G_output')(u7)
    return Model(d0, output_img, name="G")

def build_discriminator():
  df = 64
  def d_layer(layer_input, filters, f_size=4, bn=True):
      d = Conv2D(filters, kernel_size=f_size, strides=2, padding='same')(layer_input)
      if bn:
          d = BatchNormalization(momentum=0.8)(d)
      return d

  image = Input(shape=img_shape, name="real_or_fake_A")
  condition = Input(shape=img_shape, name="condition")
  combined_imgs = Concatenate(axis=-1)([image, condition])
  d1 = d_layer(combined_imgs, df, bn=False)
  d2 = d_layer(d1, df*2)
  d3 = d_layer(d2, df*4) 
  d4 = d_layer(d3, df*8)
  validity = Conv2D(1, kernel_size=4, strides=1, padding='same', name='D_output', activation='sigmoid')(d4)
  return Model([image, condition], validity, name='D')

#создаем генератор
gen = build_generator() 
gen.summary()

dis = build_discriminator()
dis.summary()

def build_vgg():
  #для feature loss создаем vgg модель
  vgg_in = Input(img_shape)
  vgg = vgg19.VGG19(include_top=False, input_shape=img_shape, input_tensor=vgg_in)
  vgg_out = vgg.get_layer('block5_conv4').output
  vgg = Model(vgg_in, vgg_out, name='vgg')
  vgg.trainable = False 
  return vgg

vgg = build_vgg()
vgg.summary()

def build_gan(generator, discriminator, vgg):
  discriminator.trainable = False
  condition = Input(img_shape, name='Condition')
  fake_img = generator(condition)
  fake_features = vgg(fake_img)
  fake_validity = discriminator([fake_img, condition])
  gan = Model(condition, [fake_validity, fake_img, fake_features])
  return gan

def train(generator, discriminator, gan, vgg, imgs, masks, epochs, batch_size):
  for epoch in range(epochs): 
    idx = np.random.choice(imgs.shape[0], imgs.shape[0], replace=False) 
    with tqdm(total=imgs.shape[0]) as pbar:
      for batch in range(imgs.shape[0]//batch_size):
        y_real = np.ones((batch_size, *discriminator.output_shape[1:])) - np.random.random_sample((batch_size, *discriminator.output_shape[1:])) * 0.2
        y_fake = np.random.random_sample((batch_size, *discriminator.output_shape[1:]))*0.2
        idx_batch = idx[batch*batch_size:(batch+1)*batch_size] 
        real_imgs = (imgs[idx_batch]/127.5) - 1 
        condition = (masks[idx_batch]/127.5) - 1
        fake_imgs = generator.predict(condition)
        d_loss_real = discriminator.train_on_batch([real_imgs, condition], y_real)
        d_loss_fake = discriminator.train_on_batch([fake_imgs, condition], y_fake)
        d_loss_total = 0.5 * np.add(d_loss_real, d_loss_fake)
        real_features = vgg.predict(real_imgs)
        y_real = np.ones((batch_size, *discriminator.output_shape[1:]))
        g_loss = gan.train_on_batch(condition, [y_real, real_imgs, real_features])
        pbar.update(batch_size)
        pbar.set_description("Epoch: {}/{}, Discriminator loss: {}, Generator loss:{}".format(epoch+1, epochs, d_loss_total[0], g_loss))

gen = build_generator() 
dis = build_discriminator()
dis.compile(loss='binary_crossentropy', optimizer=Adam(lr=1e-4, beta_1=0.5), metrics=['accuracy'])

vgg = build_vgg()
gan = build_gan(gen, dis, vgg)
gan.compile(loss=['binary_crossentropy', 'mse', 'mse'], loss_weights=[1,100,10], optimizer=Adam(lr=1e-4, beta_1=0.5))

# тренируем модель
train(gen, dis, gan, vgg, imgs, masks, 15, 16)

def sample_image(generator, imgs, masks, idx):
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
    ax[0].imshow(masks[idx])
    ax[0].set_title('маска')
    condition = masks[idx] / 127.5 - 1
    generated = (generator.predict(condition[None]) + 1) * 127.5
    ax[1].imshow(generated[0].astype('uint8'))
    ax[1].set_title('сгенерированное изображение')
    ax[2].imshow(imgs[idx]) 
    ax[2].set_title('реальное изображение')

for i in [20,100,300,500]:
   sample_image(gen, imgs, masks, i)