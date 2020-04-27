# coding=utf-8
import json

import requests


class Alerts:

	# Flag to indicate if we should use FCM for development or production
	_use_dev = False

	def __init__(self, logger):
		self._logger = logger
		self._languages = {
			'en': {
				"Print complete": 'Print complete',
				"Print progress": "Progress {}%",
				"bed-cooled": 'Printer bed below specified temperature threshold',
				"bed-warmed": 'Printer bed warmed to specified temperature and duration',
				"mmu-event": 'MMU Requires User Assistance',
				"paused-user-event": 'Printer paused for user',
				"tool0-cooled": 'Extruder below specified temperature threshold',
				"palette2-error-while-printing": 'Error {} occurred on Palette 2. Your print has been paused',
				"layer_changed": 'Layer {}'
			},
			'es': {
				"Print complete": 'Impresión completa',
				"Print progress": "Progreso {}%",
				"bed-cooled": 'Cama de la impresora por debajo del umbral de temperatura especificado',
				"bed-warmed": 'Cama de la impresora calentada a la temperatura y duración especificadas',
				"mmu-event": 'MMU requiere asistencia del usuario',
				"paused-user-event": 'Impresora en pausa esperando al usuario',
				"tool0-cooled": 'Extrusora por debajo del umbral de temperatura especificado',
				"palette2-error-while-printing": 'Error {} en Palette 2. Su impresión ha sido suspendida',
				"layer_changed": 'Capa {}'
			},
			'cs': {
				"Print complete": 'Tisk dokončen',
				"Print progress": "Vytištěno {}%",
				"bed-cooled": 'Teplota podložky pod nastavenou mezí',
				"bed-warmed": 'Podložka nahřáta na nastavenou teplotu a dobu',
				"mmu-event": 'MMU vyžaduje asistenci uživatele',
				"paused-user-event": 'Tiskárna čeká na uživatele',
				"tool0-cooled": 'Tryska nedosáhla požadované teploty',
				"palette2-error-while-printing": 'Nastala chyba {} na Palette 2. Tisk byl pozastaven',
				"layer_changed": 'Vrstva {}'
			},
			'de': {
				"Print complete": 'Druck vollständig',
				"Print progress": "Fortschritt {}%",
				"bed-cooled": 'Druckbett unterhalb der vorgegebenen Temperaturschwelle',
				"bed-warmed": 'Druckbett auf vorgegebene Temperatur für gewählte Zeit aufgeheizt',
				"mmu-event": 'MMU fordert Hilfestellung',
				"paused-user-event": 'Drucker angehalten für Benutzer',
				"tool0-cooled": 'Extruder unterhalb der vorgegebenen Schwelle',
				"palette2-error-while-printing": 'Fehler {} auf Palette 2 aufgetreten. Dein Druck wurde pausiert',
				"layer_changed": 'Schicht {}'
			},
			'it': {
				"Print complete": 'Stampa completata',
				"Print progress": "Avanzamento {}%",
				"bed-cooled": 'Piatto della stampante sotto la soglia di temperatura specificata',
				"bed-warmed": 'Piatto della stampante riscaldato alla temperatura e per la durata specificate',
				"mmu-event": 'MMU richiede l\'intervento dell\'utente',
				"paused-user-event": 'Stampante in pausa, in attesa dell\'utente',
				"tool0-cooled": 'Estensore sotto la soglia di temperatura specificata',
				"palette2-error-while-printing": 'Errore {} su Palette 2. La tua stampa è in pausa',
				"layer_changed": 'Layer {}'
			},
			'lt-LT': {
				"Print complete": 'Baigta',
				"Print progress": "Progresas {}%",
				"bed-cooled": 'Paviršius atvėso',
				"bed-warmed": 'Paviršius pasiekė nustatytą temperatūrą',
				"mmu-event": 'MMU reikalauja pagalbos',
				"paused-user-event": 'Spausdintuvas laukia vartotojo',
				"tool0-cooled": 'Ekstruderis žemiau nurodytos temperatūros ribos',
				"palette2-error-while-printing": 'Klaida {} ištiko Palette 2. Įjungta pauzė',
				"layer_changed": 'Sluoksnis {}'
			},
			'nb': {
				"Print complete": 'Utskrift ferdig',
				"Print progress": "Fremdrift {}%",
				"bed-cooled": 'Skriveflate under spesifisert temperaturgrense',
				"bed-warmed": 'Skriveflate varmet til spesifisert temperatur og varighet',
				"mmu-event": 'MMU krever tilsyn',
				"paused-user-event": 'Skriver venter på bruker',
				"tool0-cooled": 'Ekstruder under spesifisert temperaturgrense',
				"palette2-error-while-printing": 'Feil {} oppstod på Palette 2. Din print er satt på pause',
				"layer_changed": 'Lag {}'
			},
			'sv': {
				"Print complete": 'Utskrift klar',
				"Print progress": "Framsteg {}%",
				"bed-cooled": 'Skrivarbädd under angiven temperaturgräns',
				"bed-warmed": 'Skrivarbädd uppvärmd till angiven temperatur och varaktighet',
				"mmu-event": 'MMU kräver användarhjälp',
				"paused-user-event": 'Skrivare pausad för användare',
				"tool0-cooled": 'Extruder under angiven temperaturgräns',
				"palette2-error-while-printing": 'Fel {} inträffade på Palette 2. Din utskrift har pausats',
				"layer_changed": 'Lager {}'
			},
			'fr': {
				"Print complete": 'Impression terminée',
				"Print progress": "Progression {}%",
				"bed-cooled": 'Température du plateau en dessous du seuil spécifié',
				"bed-warmed": 'Plateau chauffé à la température et durée spécifiées',
				"mmu-event": 'Le MMU demande une assistance',
				"paused-user-event": 'Imprimante en pause pour l’utilisateur',
				"tool0-cooled": 'Extrudeur en dessous du seuil spécifié',
				"palette2-error-while-printing": 'Erreur {} sur Palette 2. Impression en pause',
				"layer_changed": 'Layer {}'
			},
			'ru': {
				"Print complete": 'Печать завершена',
				"Print progress": "Прогресс {}%",
				"bed-cooled": 'Температурный порог стола принтера ниже заданного',
				"bed-warmed": 'Стол принтера нагревается до заданной температуры',
				"mmu-event": 'MMU требуется помощь пользователя',
				"paused-user-event": 'Принтер приостановлен для пользователя',
				"tool0-cooled": 'Температурный порог экструдера ниже заданного',
				"palette2-error-while-printing": 'Произошла ошибка {} в Palette 2. Печать была приостановлена',
				"layer_changed": 'Слой {}'
			}
		}

	def send_alert_code(self, language_code, fcm_token, url, printer_name, event_code, category=None, image=None,
						event_param=None):
		message = None

		if language_code == 'es-419':
			# Default to Spanish instead of Latin American Spanish
			language_code = 'es'

		if language_code in self._languages:
			if event_code in self._languages[language_code]:
				message = self._languages[language_code][event_code]

		if message is None:
			self._logger.error("Missing translation for code %s in language %s" % (event_code, language_code))
			message = "Unknown code"

		if event_param is not None:
			# Replace {} with specified parameter. Only 1 parameter is supported
			message = message.format(event_param)

		self._logger.debug("Sending notification for event '%s' (%s)" % (event_code, printer_name))

		# Now send FCM notification using proper locale
		return self.send_alert(fcm_token, url, printer_name, message, category, image)

	def send_alert(self, fcm_token, url, printer_name, message, category, image):
		data = { "name": printer_name, "notification": { "title": printer_name, "message": message }, "to": fcm_token, "topic": "OctoPrint info", "android_channel_id": "push-notifs-channel", "sound": "default" }

		if category is not None:
			data["category"] = category

		headers = { "content-type": "application/json", "Authorization": "key=AAAA_15xmfU:APA91bHrfzmtnA4gMooEBDOQKkV_gdRG5AcMNLbQJ-X_JKQCx-GbDoL0jqOmcGYSumzCyieOTnYcHBSNH3PLOeyCDZthRHkEVSRJ3ysy5zAlDIYu7hz0ibxY_EWvFIoKh_AjP-LqIlo3" }

		try:
			if image:
				files = {"image": ("image.jpg", image, "image/jpeg"),
						 "json": (None, json.dumps(data), "application/json")}
				r = requests.post(url, files=files, headers=headers)
			else:
				r = requests.post(url, json=data, headers=headers)

			if r.status_code >= 400:
				self._logger.info("Notification Response: %s" % str(r.content))

			else:
				self._logger.debug("Notification Response code: %d" % r.status_code)

			return r.status_code

		except Exception as e:
			self._logger.warn("Could not send message: %s" % str(e))
			return -500

	def send_job_request(self, fcm_token, image, printer_id, printer_state, completion, url, test=False):
		data = {
			"name": printer_id, "notification": { "title": printer_id, "message": printer_state }, "to": fcm_token, "topic": "OctoPrint info", "android_channel_id": "push-notifs-channel", "sound": "default" }

		if completion:
			data["printerCompletion"] = completion

		if test:
			data["test"] = True

		headers = { "content-type": "application/json", "Authorization": "key=AAAA_15xmfU:APA91bHrfzmtnA4gMooEBDOQKkV_gdRG5AcMNLbQJ-X_JKQCx-GbDoL0jqOmcGYSumzCyieOTnYcHBSNH3PLOeyCDZthRHkEVSRJ3ysy5zAlDIYu7hz0ibxY_EWvFIoKh_AjP-LqIlo3" }

		try:
			if image:
				files = {"image": ("image.jpg", image, "image/jpeg"),
						 "json": (None, json.dumps(data), "application/json")}

				r = requests.post(url, files=files, headers=headers)
			else:
				r = requests.post(url, json=data, headers=headers)

			if r.status_code >= 400:
				self._logger.info(
					"Silent Print Job Notification Response: %s. State: %s" % (str(r.content), printer_state))

			else:
				self._logger.debug(
					"Silent Print Job Notification Response code: %d. State: %s" % (r.status_code, printer_state))

			return r.status_code

		except Exception as e:
			self._logger.info("Could not send Silent job message: %s State: %s" % (str(e), printer_state))
			return -500

	def send_bed_request(self, url, fcm_token, printer_id, event_code, temperature, minutes):
		data = {"name": printer_id, "notification": { "title": printer_id, "message": temperature }, "to": fcm_token, "topic": "OctoPrint info", "android_channel_id": "push-notifs-channel", "sound": "default" }

		if minutes:
			data["minutes"] = minutes

		headers = { "content-type": "application/json", "Authorization": "key=AAAA_15xmfU:APA91bHrfzmtnA4gMooEBDOQKkV_gdRG5AcMNLbQJ-X_JKQCx-GbDoL0jqOmcGYSumzCyieOTnYcHBSNH3PLOeyCDZthRHkEVSRJ3ysy5zAlDIYu7hz0ibxY_EWvFIoKh_AjP-LqIlo3" }

		try:
			r = requests.post(url, json=data, headers=headers)

			if r.status_code >= 400:
				self._logger.info("Silent Bed Notification Response: %s" % str(r.content))

			else:
				self._logger.debug("Silent Bed Notification Response code: %d" % r.status_code)

			return r.status_code

		except Exception as e:
			self._logger.info("Could not send Silent Bed Notification: %s" % str(e))
			return -500

	def send_mmu_request(self, url, fcm_token, printer_id):
		data = { "name": printer_id, "notification": { "title": printer_id, "message": "mmu-event" }, "to": fcm_token, "topic": "OctoPrint info", "android_channel_id": "push-notifs-channel", "sound": "default" }

		headers = { "content-type": "application/json", "Authorization": "key=AAAA_15xmfU:APA91bHrfzmtnA4gMooEBDOQKkV_gdRG5AcMNLbQJ-X_JKQCx-GbDoL0jqOmcGYSumzCyieOTnYcHBSNH3PLOeyCDZthRHkEVSRJ3ysy5zAlDIYu7hz0ibxY_EWvFIoKh_AjP-LqIlo3" }

		try:
			r = requests.post(url, json=data, headers=headers)

			if r.status_code >= 400:
				self._logger.info("Silent MMU Notification Response: %s" % str(r.content))

			else:
				self._logger.debug("Silent MMU Notification Response code: %d" % r.status_code)

			return r.status_code

		except Exception as e:
			self._logger.info("Could not send Silent MMU Notification: %s" % str(e))
			return -500

