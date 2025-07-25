import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import onnxruntime
import tf2onnx
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dataset paths
DATASET_PATH = 'images'  # Adjust to your dataset path
TRAIN_DIR = os.path.join(DATASET_PATH, 'train')
TEST_DIR = os.path.join(DATASET_PATH, 'test')

# Emotion labels
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
NUM_CLASSES = len(EMOTION_LABELS)
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 10

def create_data_generators():
    """Create train and test data generators with augmentation."""
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=20,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.2,
        zoom_range=0.2,
        horizontal_flip=True,
        fill_mode='nearest'
    )
    
    test_datagen = ImageDataGenerator(rescale=1./255)
    
    train_generator = train_datagen.flow_from_directory(
        TRAIN_DIR,
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        classes=EMOTION_LABELS
    )
    
    test_generator = test_datagen.flow_from_directory(
        TEST_DIR,
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        classes=EMOTION_LABELS
    )
    
    return train_generator, test_generator

def build_model():
    """Build and compile MobileNetV2 model."""
    base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
    
    # Freeze base layers
    for layer in base_model.layers:
        layer.trainable = False
    
    # Add custom head
    x = GlobalAveragePooling2D()(base_model.output)
    x = Dense(128, activation='relu')(x)
    x = Dropout(0.5)(x)  # Prevent overfitting
    predictions = Dense(NUM_CLASSES, activation='softmax')(x)
    
    model = Model(inputs=base_model.input, outputs=predictions)
    
    # Compile model
    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model

def train_model(model, train_generator, test_generator):
    """Train the model and return history."""
    history = model.fit(
        train_generator,
        epochs=EPOCHS,
        validation_data=test_generator,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=3,
                restore_best_weights=True
            )
        ]
    )
    return history

def evaluate_model(model, test_generator):
    """Evaluate the model on the test set."""
    test_loss, test_accuracy = model.evaluate(test_generator)
    logger.info(f"Test Loss: {test_loss:.4f}, Test Accuracy: {test_accuracy:.4f}")

def save_model(model):
    """Save the model as HDF5 and convert to ONNX."""
    # Save as HDF5
    model.save('emotion_model.h5')
    logger.info("Model saved as emotion_model.h5")
    
    # Convert to ONNX
    spec = (tf.TensorSpec((None, 224, 224, 3), tf.float32, name="input"),)
    output_path = "emotion_model.onnx"
    model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)
    with open(output_path, "wb") as f:
        f.write(model_proto.SerializeToString())
    logger.info("Model converted to emotion_model.onnx")

def main():
    logger.info("Starting model training...")
    
    # Create data generators
    train_generator, test_generator = create_data_generators()
    
    # Build model
    model = build_model()
    model.summary()
    
    # Train model
    history = train_model(model, train_generator, test_generator)
    
    # Evaluate model
    evaluate_model(model, test_generator)
    
    # Save model
    save_model(model)
    
    logger.info("Training completed.")

if __name__ == "__main__":
    main()