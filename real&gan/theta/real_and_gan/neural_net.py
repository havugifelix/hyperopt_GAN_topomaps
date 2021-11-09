"""Convolutional neural network built with Keras."""

import tensorflow
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Activation, Flatten, BatchNormalization
from tensorflow.keras.regularizers import l1,l1_l2,l2
from tensorflow.keras.layers import Conv2D, MaxPooling2D
# from tensorflow.keras.layers.advanced_activations import ELU
from sklearn.utils import class_weight
# from tensorflow.keras.utils.vis_utils import plot_model
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import os
from collections import Counter
import numpy as np
from tensorflow.keras.optimizers import *
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from sklearn.utils.multiclass import unique_labels

# from vis.utils import utils
from tensorflow.keras import activations
from utils import print_json

from tensorflow.keras.datasets import cifar100  # from keras.datasets import cifar10
# from tensorflow.keras.layers.core import K  # import keras.backend as K
from tensorflow.keras.optimizers import Adam, Nadam, RMSprop
import tensorflow as tf
from hyperopt import STATUS_OK, STATUS_FAIL

import uuid
import traceback
import os
import tensorflow.keras.backend as K

#from Custom_dataGenerator import DataGenerator
from sklearn.model_selection import train_test_split

__author__ = "Guillaume Chevalier"
__copyright__ = "Copyright 2017, Guillaume Chevalier"
__license__ = "MIT License"
__notice__ = (
    "Some further edits by Guillaume Chevalier are made on "
    "behalf of Vooban Inc. and belongs to Vooban Inc. ")
# See: https://github.com/Vooban/Hyperopt-Keras-CNN-CIFAR-100/blob/master/LICENSE"


TENSORBOARD_DIR = "TensorBoard/"
WEIGHTS_DIR = "weights/"


NB_CHANNELS = 3
im_dim=[224,224,3]

NB_CLASSES = 4



# You may want to reduce this considerably if you don't have a killer GPU:
epochs=100
STARTING_L2_REG = 0.0007

OPTIMIZER_STR_TO_CLASS = {
    'Adam': Adam,
    'Nadam': Nadam,
    'RMSprop': RMSprop,
    'SGD':SGD,
    "Adagrad":Adagrad,
    "Adadelta":Adadelta
}

# num_classes = 4
# img_rows, img_cols = 100,176
# # batch_size =16
# train_data_dir = "/home/kashraf/Research_2021/topo_data_may_v1/original/beta/train/"
# validation_data_dir = "/home/kashraf/Research_2021/topo_data_may_v1/original/beta/test/"
# # Let's use some data augmentaiton 
# datagen = ImageDataGenerator()

####---------------------------------Data Generator----------
num_classes = 4
img_rows, img_cols = 224,224
batch_size =16
train_data_dir ="/home/cvpia/felix_work/Fall2021_journal/Datasets/topos_GAN+REAL/theta/train_test/train"
validation_data_dir = "/home/cvpia/felix_work/Fall2021_journal/Datasets/topos_GAN+REAL/theta/train_test/test"

# Let's use some data augmentaiton 
train_datagen = ImageDataGenerator()
#rescale=1./255)
validation_datagen = ImageDataGenerator()
 
train_generator = train_datagen.flow_from_directory(
    train_data_dir,
    target_size=(img_rows, img_cols),
    color_mode="rgb",
    batch_size=batch_size,
    class_mode='categorical',
    shuffle=True)

validation_generator = validation_datagen.flow_from_directory(
    validation_data_dir,
    target_size=(img_rows, img_cols),
    color_mode="rgb",
    batch_size=batch_size,
    class_mode='categorical',
    shuffle=False)



def build_and_train(hype_space, save_best_weights=False, log_for_tensorboard=False):
    """Build the deep CNN model and train it."""
    K.set_learning_phase(1)
    K.set_image_data_format('channels_last')
    
    train_it=train_generator
    test_it=validation_generator
    
  #####   
    

    # if log_for_tensorboard:
    #     # We need a smaller batch size to not blow memory with tensorboard
    #     hype_space["lr_rate_mult"] = hype_space["lr_rate_mult"] / 10.0
    #     hype_space["batch_size"] = hype_space["batch_size"] / 10.0

    model = build_model(hype_space)

    # K.set_learning_phase(1)

    model_uuid = str(uuid.uuid4())[:5]

    callbacks = []

    # Weight saving callback:
    WEIGHTS_DIR="/home/cvpia/felix_work/Fall2021_journal/Modelling/hyperopt/real&gan/theta/"
    if save_best_weights:
        weights_save_path = os.path.join(
            WEIGHTS_DIR, '{}_Theta_hyp_v1.h5'.format(model_uuid))
        print("Model's weights will be saved to: {}".format(weights_save_path))
        if not os.path.exists(WEIGHTS_DIR):
            os.makedirs(WEIGHTS_DIR)

        callbacks.append(tensorflow.keras.callbacks.ModelCheckpoint(
            weights_save_path,
            monitor='val_accuracy',
            save_best_only=True, mode='max'))

    # TensorBoard logging callback:
    log_path = None
    if log_for_tensorboard:
        log_path = os.path.join(TENSORBOARD_DIR, model_uuid)
        print("Tensorboard log files will be saved to: {}".format(log_path))
        if not os.path.exists(log_path):
            os.makedirs(log_path)

        # Right now Keras's TensorBoard callback and TensorBoard itself are not
        # properly documented so we do not save embeddings (e.g.: for T-SNE).

        # embeddings_metadata = {
        #     # Dense layers only:
        #     l.name: "../10000_test_classes_labels_on_1_row_in_plain_text.tsv"
        #     for l in model.layers if 'dense' in l.name.lower()
        # }

        tb_callback = tensorflow.keras.callbacks.TensorBoard(
            log_dir=log_path,
            histogram_freq=2,
            # write_images=True, # Enabling this line would require more than 5 GB at each `histogram_freq` epoch.
            write_graph=True
            # embeddings_freq=3,
            # embeddings_layer_names=list(embeddings_metadata.keys()),
            # embeddings_metadata=embeddings_metadata
        )
        tb_callback.set_model(model)
        callbacks.append(tb_callback)

    # Train net:
    history = model.fit(
        train_it,
        epochs=epochs,
        shuffle=True,
        verbose=1,
        callbacks=callbacks,
        validation_data=test_it
    ).history

    # Test net:
    K.set_learning_phase(0)
    score = model.evaluate(test_it, verbose=0)
    max_acc = max(history['val_accuracy'])

    model_name = "model_{:.2f}_id_{}".format(round(max_acc, 2), model_uuid)
    print("Model name: {}".format(model_name))
    print(max_acc)

    # Note: to restore the model, you'll need to have a keras callback to
    # save the best weights and not the final weights. Only the result is
    # saved.
    print(history.keys())
    print(history)
    print(score)
    result = {
        # We plug "-val_fine_outputs_acc" as a
        # minimizing metric named 'loss' by Hyperopt.
        'loss': -max_acc,
        'real_loss': score[0],      
        'model_name': model_name,
        'space': hype_space,
        'history': history,
        'status': STATUS_OK
    }

    print("RESULT:")
    print_json(result)

    return model, model_name, result, log_path


def build_model(hype_space):
    """Create model according to the hyperparameter space given."""
    print("Hyperspace:")
    print(hype_space)

    input_layer = tensorflow.keras.layers.Input(
        (im_dim[0], im_dim[1], im_dim[2]))

    current_layer = random_image_mirror_left_right(input_layer)

    if hype_space['first_conv'] is not None:
        k = hype_space['first_conv']
        current_layer = tensorflow.keras.layers.Conv2D(
            filters=16, kernel_size=(k, k), strides=(1, 1),
            padding='same', activation=hype_space['activation'],
            kernel_regularizer=tensorflow.keras.regularizers.l2(
                STARTING_L2_REG * hype_space['l2_weight_reg_mult'])
        )(current_layer)
    else:
        current_layer = input_layer

    # Core loop that stacks multiple conv+pool layers, with maybe some
    # residual connections and other fluffs:
    n_filters = int(40 * hype_space['conv_hiddn_units_mult'])
    for i in range(hype_space['nb_conv_pool_layers']):
        print(i)
        print(n_filters)
        print(current_layer.shape)

        current_layer = convolution(current_layer, n_filters, hype_space)
        if hype_space['use_BN']:
            current_layer = bn(current_layer)
        print(current_layer.shape)

        deep_enough_for_res = hype_space['conv_pool_res_start_idx']
        if i >= deep_enough_for_res and hype_space['residual'] is not None:
            current_layer = residual(current_layer, n_filters, hype_space)
            print(current_layer.shape)

        current_layer = auto_choose_pooling(
            current_layer, n_filters, hype_space)
        print(current_layer.shape)

        current_layer = dropout(current_layer, hype_space)

        n_filters *= 2

    # Fully Connected (FC) part:
    current_layer = tensorflow.keras.layers.Flatten()(current_layer)
    print(current_layer.shape)

    current_layer = tensorflow.keras.layers.Dense(
        units=int(1000 * hype_space['fc_units_1_mult']),
        activation=hype_space['activation'],
        kernel_regularizer=tensorflow.keras.regularizers.l2(
            STARTING_L2_REG * hype_space['l2_weight_reg_mult'])
    )(current_layer)
    print(current_layer.shape)

    current_layer = dropout(
        current_layer, hype_space, for_convolution_else_fc=False)

    if hype_space['one_more_fc'] is not None:
        current_layer = tensorflow.keras.layers.Dense(
            units=int(750 * hype_space['one_more_fc']),
            activation=hype_space['activation'],
            kernel_regularizer=tensorflow.keras.regularizers.l2(
                STARTING_L2_REG * hype_space['l2_weight_reg_mult'])
        )(current_layer)
        print(current_layer.shape)

        current_layer = dropout(
            current_layer, hype_space, for_convolution_else_fc=False)

    # Two heads as outputs:
    output_layer = tensorflow.keras.layers.Dense(
        units=NB_CLASSES,
        activation="softmax",
        kernel_regularizer=tensorflow.keras.regularizers.l2(
            STARTING_L2_REG * hype_space['l2_weight_reg_mult']),
    )(current_layer)

    # Finalize model:
    model = tensorflow.keras.models.Model(
        inputs=[input_layer],
        outputs=[output_layer]
    )
    model.compile(
        optimizer=OPTIMIZER_STR_TO_CLASS[hype_space['optimizer']](
            lr=0.001 * hype_space['lr_rate_mult']
        ),
        loss='categorical_crossentropy',
 
        metrics=['accuracy']
    )
    return model


def random_image_mirror_left_right(input_layer):
    """
    Flip each image left-right like in a mirror, randomly, even at test-time.
    This acts as a data augmentation technique. See:
    https://stackoverflow.com/questions/39574999/tensorflow-tf-image-functions-on-an-image-batch
    """
    return tensorflow.keras.layers.Lambda(function=lambda batch_imgs: tf.map_fn(
        lambda img: tf.image.random_flip_left_right(img), batch_imgs
    )
    )(input_layer)


def bn(prev_layer):
    """Perform batch normalisation."""
    return BatchNormalization()(prev_layer)


def dropout(prev_layer, hype_space, for_convolution_else_fc=True):
    """Add dropout after a layer."""
    if for_convolution_else_fc:
        return tensorflow.keras.layers.Dropout(
            rate=hype_space['conv_dropout_drop_proba']
        )(prev_layer)
    else:
        return tensorflow.keras.layers.Dropout(
            rate=hype_space['fc_dropout_drop_proba']
        )(prev_layer)


def convolution(prev_layer, n_filters, hype_space, force_ksize=None):
    """Basic convolution layer, parametrized by the hype_space."""
    if force_ksize is not None:
        k = force_ksize
    else:
        k = int(round(hype_space['conv_kernel_size']))
    return  tensorflow.keras.layers.Conv2D(
        filters=n_filters, kernel_size=(k, k), strides=(1, 1),
        padding='same', activation=hype_space['activation'],
        kernel_regularizer=tensorflow.keras.regularizers.l2(
            STARTING_L2_REG * hype_space['l2_weight_reg_mult'])
    )(prev_layer)


def residual(prev_layer, n_filters, hype_space):
    """Some sort of residual layer, parametrized by the hype_space."""
    current_layer = prev_layer
    for i in range(int(round(hype_space['residual']))):
        lin_current_layer = tensorflow.keras.layers.Conv2D(
            filters=n_filters, kernel_size=(1, 1), strides=(1, 1),
            padding='same', activation='linear',
            kernel_regularizer=tensorflow.keras.regularizers.l2(
                STARTING_L2_REG * hype_space['l2_weight_reg_mult'])
        )(current_layer)

        layer_to_add = dropout(current_layer, hype_space)
        layer_to_add = convolution(
            layer_to_add, n_filters, hype_space,
            force_ksize=int(round(hype_space['res_conv_kernel_size'])))

        current_layer = tensorflow.keras.layers.add([
            lin_current_layer,
            layer_to_add
        ])
        if hype_space['use_BN']:
            current_layer = bn(current_layer)
    if not hype_space['use_BN']:
        current_layer = bn(current_layer)

    return bn(current_layer)


def auto_choose_pooling(prev_layer, n_filters, hype_space):
    """Deal with pooling in convolution steps."""
    if hype_space['pooling_type'] == 'all_conv':
        current_layer = convolution_pooling(
            prev_layer, n_filters, hype_space)

    elif hype_space['pooling_type'] == 'inception':
        current_layer = inception_reduction(prev_layer, n_filters, hype_space)

    elif hype_space['pooling_type'] == 'avg':
        current_layer =  tensorflow.keras.layers.AveragePooling2D(
            pool_size=(2, 2)
        )(prev_layer)

    else:  # 'max'
        current_layer =  tensorflow.keras.layers.MaxPooling2D(
            pool_size=(2, 2)
        )(prev_layer)

    return current_layer


def convolution_pooling(prev_layer, n_filters, hype_space):
    """
    Pooling with a convolution of stride 2.
    See: https://arxiv.org/pdf/1412.6806.pdf
    """
    current_layer = tensorflow.keras.layers.Conv2D(
        filters=n_filters, kernel_size=(3, 3), strides=(2, 2),
        padding='same', activation='linear',
        kernel_regularizer=tensorflow.keras.regularizers.l2(
            STARTING_L2_REG * hype_space['l2_weight_reg_mult'])
    )(prev_layer)

    if hype_space['use_BN']:
        current_layer = bn(current_layer)

    return current_layer


def inception_reduction(prev_layer, n_filters, hype_space):
    """
    Reduction block, vaguely inspired from inception.
    See: https://arxiv.org/pdf/1602.07261.pdf
    """
    n_filters_a = int(n_filters * 0.33 + 1)
    n_filters = int(n_filters * 0.4 + 1)

    conv1 = convolution(prev_layer, n_filters_a, hype_space, force_ksize=3)
    conv1 = convolution_pooling(prev_layer, n_filters, hype_space)

    conv2 = convolution(prev_layer, n_filters_a, hype_space, 1)
    conv2 = convolution(conv2, n_filters, hype_space, 3)
    conv2 = convolution_pooling(conv2, n_filters, hype_space)

    conv3 = convolution(prev_layer, n_filters, hype_space, force_ksize=1)
    conv3 = tensorflow.keras.layers.MaxPooling2D(
        pool_size=(3, 3), strides=(2, 2), padding='same'
    )(conv3)

    current_layer = tensorflow.keras.layers.concatenate([conv1, conv2, conv3], axis=-1)

    return current_layer
