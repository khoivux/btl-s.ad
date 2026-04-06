import tensorflow as tf
import tensorflow_recommenders as tfrs
import numpy as np

class UserTower(tf.keras.Model):
    def __init__(self):
        super().__init__()
        self.dense = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(32) # Embedding Dim
        ])

    def call(self, inputs):
        # inputs: numerical features (search_count, cart_count, orders_count, etc.)
        return self.dense(inputs)

class ItemTower(tf.keras.Model):
    def __init__(self):
        super().__init__()
        self.dense = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(32) # Match User Embedding Dim
        ])

    def call(self, inputs):
        # inputs: book numerical features (price, category_id_onehot, reviews_count, avg_rating)
        return self.dense(inputs)

class TwoTowerBehaviorModel(tfrs.Model):
    def __init__(self, user_model, item_model):
        super().__init__()
        self.user_model = user_model
        self.item_model = item_model
        self.task = tfrs.tasks.Retrieval()

    def compute_loss(self, features, training=False):
        user_embeddings = self.user_model(features["user_features"])
        item_embeddings = self.item_model(features["item_features"])
        return self.task(user_embeddings, item_embeddings)
