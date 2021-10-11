# coding=utf-8
import json

import requests


class Alerts:

	# Flag to indicate if we should use APNS for development or production
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
				"tool0-warmed": 'Extruder warmed to specified temperature',
				"palette2-error-while-printing": 'Error {} occurred on Palette 2. Your print has been paused',
				"layer_changed": 'Layer {}',
				"soc_temp_exceeded": 'SoC Temperature above threshold {}°',
				"thermal-runaway": 'DANGER: Possible thermal runaway detected!'
			},
			'es': {
				"Print complete": 'Impresión completa',
				"Print progress": "Progreso {}%",
				"bed-cooled": 'Cama de la impresora por debajo del umbral de temperatura especificado',
				"bed-warmed": 'Cama de la impresora calentada a la temperatura y duración especificadas',
				"mmu-event": 'MMU requiere asistencia del usuario',
				"paused-user-event": 'Impresora en pausa esperando al usuario',
				"tool0-cooled": 'Extrusora por debajo del umbral de temperatura especificado',
				"tool0-warmed": 'Extrusora calentada a la temperatura especificada',
				"palette2-error-while-printing": 'Error {} en Palette 2. Su impresión ha sido suspendida',
				"layer_changed": 'Capa {}',
				"soc_temp_exceeded": 'Temperatura del SoC por arriba de {}°',
				"thermal-runaway": 'PELIGRO: ¡Posible fuga térmica detectada!'
			},
			'cs': {
				"Print complete": 'Tisk dokončen',
				"Print progress": "Vytištěno {}%",
				"bed-cooled": 'Teplota podložky pod nastavenou mezí',
				"bed-warmed": 'Podložka nahřáta na nastavenou teplotu a dobu',
				"mmu-event": 'MMU vyžaduje asistenci uživatele',
				"paused-user-event": 'Tiskárna čeká na uživatele',
				"tool0-cooled": 'Tryska nedosáhla požadované teploty',
				"tool0-warmed": 'Tryska se zahřeje na stanovenou teplotu',
				"palette2-error-while-printing": 'Nastala chyba {} na Palette 2. Tisk byl pozastaven',
				"layer_changed": 'Vrstva {}',
				"soc_temp_exceeded": 'Teplota SoC přesahuje hranici {}°',
				"thermal-runaway": 'NEBEZPEČÍ: Detekována možná ztráta teploty!'
			},
			'de': {
				"Print complete": 'Druck vollständig',
				"Print progress": "Fortschritt {}%",
				"bed-cooled": 'Druckbett unterhalb der vorgegebenen Temperaturschwelle',
				"bed-warmed": 'Druckbett auf vorgegebene Temperatur für gewählte Zeit aufgeheizt',
				"mmu-event": 'MMU fordert Hilfestellung',
				"paused-user-event": 'Drucker angehalten für Benutzer',
				"tool0-cooled": 'Extruder unterhalb der vorgegebenen Schwelle',
				"tool0-warmed": 'Extruder auf spezifizierte Temperatur erwärmt',
				"palette2-error-while-printing": 'Fehler {} auf Palette 2 aufgetreten. Dein Druck wurde pausiert',
				"layer_changed": 'Schicht {}',
				"soc_temp_exceeded": 'SoC Temperatur oberhalb der Schwelle {}°',
				"thermal-runaway": 'Gefahr: Möglicher thermischer Runaway erkannt!'
			},
			'it': {
				"Print complete": 'Stampa completata',
				"Print progress": "Avanzamento {}%",
				"bed-cooled": 'Piatto della stampante sotto la soglia di temperatura specificata',
				"bed-warmed": 'Piatto della stampante riscaldato alla temperatura e per la durata specificate',
				"mmu-event": 'MMU richiede l\'intervento dell\'utente',
				"paused-user-event": 'Stampante in pausa, in attesa dell\'utente',
				"tool0-cooled": 'Estensore sotto la soglia di temperatura specificata',
				"tool0-warmed": 'Estensore riscaldato alla temperatura specificata',
				"palette2-error-while-printing": 'Errore {} su Palette 2. La tua stampa è in pausa',
				"layer_changed": 'Layer {}',
				"soc_temp_exceeded": 'Temperatura SoC oltre la soglia di {}°',
				"thermal-runaway": 'PERICOLO: è stato rilevata una possibile fuga termica (thermal runaway)!'
			},
			'lt-LT': {
				"Print complete": 'Baigta',
				"Print progress": "Progresas {}%",
				"bed-cooled": 'Paviršius atvėso',
				"bed-warmed": 'Paviršius pasiekė nustatytą temperatūrą',
				"mmu-event": 'MMU reikalauja pagalbos',
				"paused-user-event": 'Spausdintuvas laukia vartotojo',
				"tool0-cooled": 'Ekstruderis žemiau nurodytos temperatūros ribos',
				"tool0-warmed": 'Ekstruderis pašildomas iki nurodytos temperatūros',
				"palette2-error-while-printing": 'Klaida {} ištiko Palette 2. Įjungta pauzė',
				"layer_changed": 'Sluoksnis {}',
				"soc_temp_exceeded": 'SoC temparatūra virš ribos {}°',
				"thermal-runaway": 'PAVOJUS! Galimai aptiktas temperatūros nuokrypis'
			},
			'nb': {
				"Print complete": 'Utskrift ferdig',
				"Print progress": "Fremdrift {}%",
				"bed-cooled": 'Skriveflate under spesifisert temperaturgrense',
				"bed-warmed": 'Skriveflate varmet til spesifisert temperatur og varighet',
				"mmu-event": 'MMU krever tilsyn',
				"paused-user-event": 'Skriver venter på bruker',
				"tool0-cooled": 'Ekstruder under spesifisert temperaturgrense',
				"tool0-warmed": 'Ekstruder varmet opp til spesifisert temperatur',
				"palette2-error-while-printing": 'Feil {} oppstod på Palette 2. Din print er satt på pause',
				"layer_changed": 'Lag {}',
				"soc_temp_exceeded": 'SoC Temperatur over terskelen {}°',
				"thermal-runaway": 'FARE: Mulig termisk runaway oppdaget!'
			},
			'sv': {
				"Print complete": 'Utskrift klar',
				"Print progress": "Framsteg {}%",
				"bed-cooled": 'Skrivarbädd under angiven temperaturgräns',
				"bed-warmed": 'Skrivarbädd uppvärmd till angiven temperatur och varaktighet',
				"mmu-event": 'MMU kräver användarhjälp',
				"paused-user-event": 'Skrivare pausad för användare',
				"tool0-cooled": 'Extruder under angiven temperaturgräns',
				"tool0-warmed": 'Extruder värms upp till specificerad temperatur',
				"palette2-error-while-printing": 'Fel {} inträffade på Palette 2. Din utskrift har pausats',
				"layer_changed": 'Lager {}',
				"soc_temp_exceeded": 'SoC-temperatur över tröskeln {}°',
				"thermal-runaway": 'FARA: Möjlig värmekörning upptäckt!'
			},
			'fr': {
				"Print complete": 'Impression terminée',
				"Print progress": "Progression {}%",
				"bed-cooled": 'Température du plateau en dessous du seuil spécifié',
				"bed-warmed": 'Plateau chauffé à la température et durée spécifiées',
				"mmu-event": 'Le MMU demande une assistance',
				"paused-user-event": 'Imprimante en pause pour l’utilisateur',
				"tool0-cooled": 'Extrudeur en dessous du seuil spécifié',
				"tool0-warmed": 'Extrudeuse chauffée à la température spécifiée',
				"palette2-error-while-printing": 'Erreur {} sur Palette 2. Impression en pause',
				"layer_changed": 'Layer {}',
				"soc_temp_exceeded": 'SoC Température au-dessus du seuil {}°',
				"thermal-runaway": 'DANGER: Possible emballement thermique détecté !'
			},
			'ru': {
				"Print complete": 'Печать завершена',
				"Print progress": "Прогресс {}%",
				"bed-cooled": 'Температурный порог стола принтера ниже заданного',
				"bed-warmed": 'Стол принтера нагревается до заданной температуры',
				"mmu-event": 'MMU требуется помощь пользователя',
				"paused-user-event": 'Принтер приостановлен для пользователя',
				"tool0-cooled": 'Температурный порог экструдера ниже заданного',
				"tool0-warmed": 'Экструдер нагрет до заданной температуры',
				"palette2-error-while-printing": 'Произошла ошибка {} в Palette 2. Печать была приостановлена',
				"layer_changed": 'Слой {}',
				"soc_temp_exceeded": 'Температура SoC выше порога {}°',
				"thermal-runaway": 'ОПАСНОСТЬ: Возможный термический бег выявлен!'
			},
			'nl': {
				"Print complete": 'Print compleet',
				"Print progress": "Voortgang {}%",
				"bed-cooled": 'Printerbed onder de opgegeven temperatuurdrempel',
				"bed-warmed": 'Printerbed opgewarmd tot gespecificeerde temperatuur en duur',
				"mmu-event": 'MMU vereist gebruikershulp',
				"paused-user-event": 'Printer is gepauzeerd voor gebruiker',
				"tool0-cooled": 'Extruder onder de opgegeven temperatuurdrempelwaarde',
				"tool0-warmed": 'Extruder verwarmd tot gespecificeerde temperatuur',
				"palette2-error-while-printing": 'Fout {} heeft plaatsgevonden op palet 2. Uw afdruk is gepauzeerd',
				"layer_changed": 'Laag {}',
				"soc_temp_exceeded": 'SoC-temperatuur boven drempel {}°',
				"thermal-runaway": 'Gevaar: mogelijk thermal runaway gedecteerd!'
			},
			'zh-Hans': {
				"Print complete": '打印完成',
				"Print progress": "打印 {}％",
				"bed-cooled": '打印机床低于指定温度阈值',
				"bed-warmed": '打印机床加热到指定的温度和持续时间',
				"mmu-event": 'MMU 需要用户协助',
				"paused-user-event": '打印机为用户暂停',
				"tool0-cooled": '挤出机低于指定温度阈值',
				"tool0-warmed": '挤出机加热到指定温度',
				"palette2-error-while-printing": '错误 {} 发生在Palette 2 上。您的打印已暂停',
				"layer_changed": '{} 层',
				"soc_temp_exceeded": 'SoC 温度高于阈值 {}°',
				"thermal-runaway": '危险：检测到可能的热失控'
			}
		}

	def send_alert_code(self, settings, language_code, apns_token, url, printer_name, event_code, category=None,
						image=None, event_param=None, apns_dict=None):
		message = None
		if language_code == 'es-419':
			# Default to Spanish instead of Latin American Spanish
			language_code = 'es'
		if language_code == 'lt':
			language_code = 'lt-LT'
		if language_code == 'zh':
			language_code = 'zh-Hans'

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

		# Now send APNS notification using proper locale
		return self.send_alert(settings, apns_token, url, printer_name, message, category, image, apns_dict)

	def send_alert(self, settings, apns_token, url, printer_name, message, category, image, apns_dict=None):
		"""
		Send Push Notification to OctoPod app running on iPhone (includes Apple Watch and iPad)
		via the OctoPod APNS service.

		:param settings: Plugin settings
		:param apns_token: APNS token that uniquely identifies the iOS app installed in the iPhone
		:param url: endpoint to hit of OctoPod APNS service
		:param printer_name: Title to display in the notification
		:param message: Message to include in the notification
		:param category: Optional. Category supported by OctoPod app. Actions depend on the category
		:param image: Optional. Image to include in the notification
		:param apns_dict: Optional. Extra information to include in the notification. Useful for actions.
		:return: HTTP status code returned by OctoPod APNS service (see url param)
		"""
		data = {"tokens": [apns_token], "title": printer_name, "message": message, "sound": "default",
				"printerName": printer_name, "useDev": self._use_dev}

		custom_sound = settings.get(["sound_notification"])
		if custom_sound:
			data['sound'] = custom_sound

		if category is not None:
			data['category'] = category

		if apns_dict is not None:
			data.update(apns_dict)

		try:
			if image:
				files = {'image': ("image.jpg", image, "image/jpeg"),
						 'json': (None, json.dumps(data), "application/json")}

				r = requests.post(url, files=files)
			else:
				r = requests.post(url, json=data)

			if r.status_code >= 400:
				self._logger.info("Notification Response: %s" % str(r.content))
			else:
				self._logger.debug("Notification Response code: %d" % r.status_code)
			return r.status_code
		except Exception as e:
			self._logger.warn("Could not send message: %s" % str(e))
			return -500

	# Silent notifications. Legacy mode uses them and also to ask OctoPod app to update
	# complications of Apple Watch

	def send_job_request(self, apns_token, image, printer_id, printer_state, completion, url, test=False):
		data = {"tokens": [apns_token], "printerID": printer_id, "printerState": printer_state, "silent": True,
				"useDev": self._use_dev}

		if completion:
			data["printerCompletion"] = completion

		if test:
			data["test"] = True

		try:
			if image:
				files = {'image': ("image.jpg", image, "image/jpeg"),
						 'json': (None, json.dumps(data), "application/json")}

				r = requests.post(url, files=files)
			else:
				r = requests.post(url, json=data)

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

	def send_bed_request(self, url, apns_token, printer_id, event_code, temperature, minutes):
		data = {"tokens": [apns_token], "printerID": printer_id, "eventCode": event_code, "temperature": temperature,
				"silent": True, "useDev": self._use_dev}

		if minutes:
			data["minutes"] = minutes

		try:
			r = requests.post(url, json=data)

			if r.status_code >= 400:
				self._logger.info("Silent Bed Notification Response: %s" % str(r.content))
			else:
				self._logger.debug("Silent Bed Notification Response code: %d" % r.status_code)
			return r.status_code
		except Exception as e:
			self._logger.info("Could not send Silent Bed Notification: %s" % str(e))
			return -500

	def send_mmu_request(self, url, apns_token, printer_id):
		data = {"tokens": [apns_token], "printerID": printer_id, "eventCode": "mmu-event", "silent": True,
				"useDev": self._use_dev}

		try:
			r = requests.post(url, json=data)

			if r.status_code >= 400:
				self._logger.info("Silent MMU Notification Response: %s" % str(r.content))
			else:
				self._logger.debug("Silent MMU Notification Response code: %d" % r.status_code)
			return r.status_code
		except Exception as e:
			self._logger.info("Could not send Silent MMU Notification: %s" % str(e))
			return -500
