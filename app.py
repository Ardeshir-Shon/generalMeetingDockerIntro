from flask import Flask, render_template, jsonify, send_file
import tensorflow as tf
import redis
import numpy as np
import random
from tensorflow.keras.datasets import mnist

app = Flask(__name__)
db = redis.StrictRedis(host='redis', port=6379, db=0)

(train_images, train_labels), (test_images, test_labels) = mnist.load_data()
train_images = train_images / 255.0
test_images = test_images / 255.0

model = tf.keras.models.Sequential([
    tf.keras.layers.Flatten(input_shape=(28, 28)),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(10, activation='softmax')
])

model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

model.fit(train_images, train_labels, epochs=5)


@app.route('/get_predictions', methods=['GET'])
def get_predictions():
    indices = [random.randint(0, len(test_images) - 1) for _ in range(10)]
    images = test_images[indices]
    true_labels = test_labels[indices].tolist()  # Convert to list of native int types
    predicted_labels = model.predict(images)
    predicted_labels = np.argmax(predicted_labels, axis=1).tolist()  # Convert to list of native int types

    converted_predicted_labels = np.array(predicted_labels, dtype=int)
    converted_true_labels = np.array(true_labels, dtype=int)

    correct_predictions = int(np.sum(converted_predicted_labels == converted_true_labels))  # Convert to native int type
    
    app.logger.info(f'predicted_labels: {predicted_labels}')
    app.logger.info(f'true_labels: {true_labels}')
    app.logger.info(f'correct_predictions: {correct_predictions}')
    
    db.incrby('correct_predictions', correct_predictions)
    db.incrby('total_predictions', 10)

    # Decode the Redis values to strings and convert to int for JSON serialization
    total_predictions = int(db.get('total_predictions').decode())
    accumulated_correct_predictions = int(db.get('correct_predictions').decode())

    app.logger.info('Redis values:')
    app.logger.info(f'total_predictions: {total_predictions}')
    app.logger.info(f'accumulated_correct_predictions: {accumulated_correct_predictions}')

    return jsonify({
        'images': images.tolist(),
        'true_labels': true_labels,
        'predicted_labels': predicted_labels,
        'correct_predictions': correct_predictions,
        'total_predictions': total_predictions,
        'accuracy': accumulated_correct_predictions / total_predictions if total_predictions > 0 else 0
    })

@app.route('/download_model', methods=['GET'])
def download_model():
    model.save('mnist_model.h5')
    return send_file('mnist_model.h5', as_attachment=True)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
