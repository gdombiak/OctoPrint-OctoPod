from io import BytesIO  ## for Python 2 & 3

import requests
from PIL import Image


class BaseNotification:

	def __init__(self, logger):
		self._logger = logger

	def image(self, snapshot_url, hflip, vflip, rotate):
		"""
		Create an image by getting an image form the setting webcam-snapshot.
		Transpose this image according the settings and returns it
		:return:
		"""
		self._logger.debug("Snapshot URL: %s " % str(snapshot_url))
		image = requests.get(snapshot_url, stream=True).content

		try:
			# Reduce resolution of image to prevent 400 error when uploading content
			# Besides this saves network bandwidth and iOS device or Apple Watch
			# cannot tell the difference in resolution
			image_obj = Image.open(BytesIO(image))
			x, y = image_obj.size
			if x > 1640 or y > 1232:
				size = 1640, 1232
				image_obj.thumbnail(size, Image.ANTIALIAS)
				output = BytesIO()
				image_obj.save(output, format="JPEG")
				image = output.getvalue()
				output.close()
		except Exception as e:
			self._logger.debug("Error reducing resolution of image: %s" % str(e))

		if hflip or vflip or rotate:
			try:
				# https://www.blog.pythonlibrary.org/2017/10/05/how-to-rotate-mirror-photos-with-python/
				image_obj = Image.open(BytesIO(image))
				if hflip:
					image_obj = image_obj.transpose(Image.FLIP_LEFT_RIGHT)
				if vflip:
					image_obj = image_obj.transpose(Image.FLIP_TOP_BOTTOM)
				if rotate:
					image_obj = image_obj.rotate(90)

				# https://stackoverflow.com/questions/646286/python-pil-how-to-write-png-image-to-string/5504072
				output = BytesIO()
				image_obj.save(output, format="JPEG")
				image = output.getvalue()
				output.close()
			except Exception as e:
				self._logger.debug("Error rotating image: %s" % str(e))

		return image
