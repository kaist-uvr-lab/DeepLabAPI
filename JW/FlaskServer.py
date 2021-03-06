import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()

import ujson
#import hyperjson
import numpy as np
from PIL import Image
import time
from flask import Flask, request
from flask_cors import CORS
import base64
import cv2

from JW.DeepLabV3 import DeepLabModel
from matplotlib import gridspec
from matplotlib import pyplot as plt

tf.debugging.set_log_device_placement(True)
download_path1 = "./model/deeplabv3_xception_ade20k_train_2018_05_29.tar.gz"
download_path2 = "./model/deeplabv3_mnv2_ade20k_train_2018_12_03.tar.gz"
saved_model_path = './model/deeplab_ade20k/10/'

#MODEL = DeepLabModel(download_path1)
#MODEL.store(saved_model_path)
#resized_img, res =MODEL.runWithCV('./data/ki_corridor/1.png')
#plt.figure(figsize=(20, 15))
#plt.imshow(res)
#plt.show()


###########################
# ADE20K Label names & Color map
###########################

def create_pascal_label_colormap():
  """Creates a label colormap used in PASCAL VOC segmentation benchmark.

  Returns:
    A Colormap for visualizing segmentation results.
  """
  colormap = np.zeros((256, 3), dtype=int)
  ind = np.arange(256, dtype=int)

  for shift in reversed(range(8)):
    for channel in range(3):
      colormap[:, channel] |= ((ind >> channel) & 1) << shift
    ind >>= 3

  return colormap


def label_to_color_image(label):
  """Adds color defined by the dataset colormap to the label.

  Args:
    label: A 2D array with integer type, storing the segmentation label.

  Returns:
    result: A 2D array with floating type. The element of the array
      is the color indexed by the corresponding element in the input label
      to the PASCAL color map.

  Raises:
    ValueError: If label is not of rank 2 or its value is larger than color
      map maximum entry.
  """
  if label.ndim != 2:
    raise ValueError('Expect 2-D input label')

  colormap = create_pascal_label_colormap()

  if np.max(label) >= len(colormap):
    raise ValueError('label value too large.')

  return colormap[label]

def vis_segmentation(image, seg_map):
  """Visualizes input image, segmentation map and overlay view."""
  plt.figure(figsize=(15, 5))
  grid_spec = gridspec.GridSpec(1, 4, width_ratios=[6, 6, 6, 1])

  plt.subplot(grid_spec[0])
  plt.imshow(image)
  plt.axis('off')
  plt.title('input image')

  plt.subplot(grid_spec[1])
  seg_image = label_to_color_image(seg_map).astype(np.uint8)
  plt.imshow(seg_image)
  plt.axis('off')
  plt.title('segmentation map')

  plt.subplot(grid_spec[2])
  plt.imshow(image)
  plt.imshow(seg_image, alpha=0.7)
  plt.axis('off')
  plt.title('segmentation overlay')

  unique_labels = np.unique(seg_map)
  ax = plt.subplot(grid_spec[3])
  plt.imshow(
      FULL_COLOR_MAP[unique_labels].astype(np.uint8), interpolation='nearest')
  ax.yaxis.tick_right()
  plt.yticks(range(len(unique_labels)), LABEL_NAMES[unique_labels])
  plt.xticks([], [])
  ax.tick_params(width=0.0)
  plt.grid('off')
  plt.show()

def GetColorMap(image, seg_map):
    seg_image = label_to_color_image(seg_map).astype(np.uint8)
    #unique_labels = np.unique(seg_map)

    #print(FULL_LABEL_MAP[unique_labels].astype(np.uint8))
    #print(unique_labels)
    return seg_image

LABEL_NAMES = np.array(['wall' ,'building' ,'sky' ,'floor' ,'tree' ,'ceiling' ,'road' ,'bed' ,'windowpane' ,'grass' ,'cabinet' ,'sidewalk' ,'person' ,'earth' ,'door' ,'table' ,'mountain' ,'plant' ,'curtain' ,'chair' ,'car' ,'water' ,'painting' ,'sofa' ,'shelf' ,'house' ,'sea' ,'mirror' ,'rug' ,'field' ,'armchair' ,'seat' ,'fence' ,'desk' ,'rock' ,'wardrobe' ,'lamp' ,'bathtub' ,'railing' ,'cushion' ,'base' ,'box' ,'column' ,'signboard' ,'chest of drawers' ,'counter' ,'sand' ,'sink' ,'skyscraper' ,'fireplace' ,'refrigerator' ,'grandstand' ,'path' ,'stairs' ,'runway' ,'case' ,'pool table' ,'pillow' ,'screen door' ,'stairway' ,'river' ,'bridge' ,'bookcase' ,'blind' ,'coffee table' ,'toilet' ,'flower' ,'book' ,'hill' ,'bench' ,'countertop' ,'stove' ,'palm' ,'kitchen island' ,'computer' ,'swivel chair' ,'boat' ,'bar' ,'arcade machine' ,'hovel' ,'bus' ,'towel' ,'light' ,'truck' ,'tower' ,'chandelier' ,'awning' ,'streetlight' ,'booth' ,'television' ,'airplane' ,'dirt track' ,'apparel' ,'pole' ,'land' ,'bannister' ,'escalator' ,'ottoman' ,'bottle' ,'buffet' ,'poster' ,'stage' ,'van' ,'ship' ,'fountain' ,'conveyer belt' ,'canopy' ,'washer' ,'plaything' ,'swimming pool' ,'stool' ,'barrel' ,'basket' ,'waterfall' ,'tent' ,'bag' ,'minibike' ,'cradle' ,'oven' ,'ball' ,'food' ,'step' ,'tank' ,'trade name' ,'microwave' ,'pot' ,'animal' ,'bicycle' ,'lake' ,'dishwasher' ,'screen' ,'blanket' ,'sculpture' ,'hood' ,'sconce' ,'vase' ,'traffic light' ,'tray' ,'ashcan' ,'fan' ,'pier' ,'crt screen' ,'plate' ,'monitor' ,'bulletin board' ,'shower' ,'radiator' ,'glass' ,'clock' ,'flag'])
FULL_LABEL_MAP = np.arange(len(LABEL_NAMES)).reshape(len(LABEL_NAMES), 1)
FULL_COLOR_MAP = label_to_color_image(FULL_LABEL_MAP)

##################################################
# API part
##################################################
app = Flask(__name__)
cors = CORS(app)
@app.route("/api/predict", methods=['POST'])
def predict():
    start = time.time()

    #parsing requested data
    params = ujson.loads(request.data)
    x_in = base64.b64decode(params['image'])
    width = int(params['w'])
    height = int(params['h'])

    #Convert PIL Image
    ######
    img_array = np.frombuffer(x_in, dtype = np.uint8)
    img_cv = cv2.imdecode(img_array,1)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img_cv)

    ##################################################
    # Tensorflow part
    ##################################################
    resized_img, seg_map = MODEL.run(img)

    ##################################################
    # END Tensorflow part
    ##################################################

    json_data = ujson.dumps({'seg_label': seg_map.tolist(), 'w':len(seg_map[0]), 'h':len(seg_map)})
    print("Time spent handling the request: %f" % (time.time() - start))

    return json_data
##################################################
# END API part
##################################################

if __name__ == "__main__":

    ##################################################
    # Tensorflow part
    ##################################################
    #print("Num GPUs Available: ", len(tf.config.experimental.list_physical_devices('GPU')))
    #print(tf.Session())

    MODEL = DeepLabModel(download_path1)
    graph = MODEL.graph
    x = graph.get_tensor_by_name(MODEL.INPUT_TENSOR_NAME)
    y = graph.get_tensor_by_name(MODEL.OUTPUT_TENSOR_NAME)

    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.8) #0.95
    sess_config = tf.ConfigProto(gpu_options=gpu_options)
    persistent_sess = tf.Session(graph=graph, config=sess_config)
    ##################################################
    # END Tensorflow part
    ##################################################

    print('Starting the API')
    #app.run(host='143.248.94.189', port = 35005)
    app.run(host='143.248.95.112', port=35005)