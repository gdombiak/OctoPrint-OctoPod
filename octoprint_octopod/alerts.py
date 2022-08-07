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
				"Print progress": "Progress {PrintProgress}%",
				"bed-cooled": 'Printer bed below specified temperature threshold ({BedThreshold}°)',
				"bed-warmed": 'Printer bed warmed to specified temperature ({BedThreshold}°) for {Duration} minutes',
				"mmu-event": 'MMU Requires User Assistance',
				"paused-user-event": 'Printer paused for user',
				"tool0-cooled": 'Extruder below specified temperature threshold ({Tool0Threshold}°)',
				"tool0-warmed": 'Extruder warmed to specified temperature ({Tool0Threshold}°)',
				"palette2-error-while-printing": 'Error {PaletteError} occurred on Palette 2. Your print has been paused',
				"layer_changed": 'Layer {PrintLayer}',
				"soc_temp_exceeded": 'SoC Temperature ({SoCTemp}°) above threshold {SoCThreshold}°',
				"thermal-runaway": 'DANGER: Possible thermal runaway detected!'
			},
			'es': {
				"Print complete": 'Impresión completa',
				"Print progress": "Progreso {PrintProgress}%",
				"bed-cooled": 'Cama de la impresora por debajo del umbral de temperatura especificado ({BedThreshold}°)',
				"bed-warmed": 'Cama de la impresora calentada a la temperatura ({BedThreshold}°) durante {Duration} minutos',
				"mmu-event": 'MMU requiere asistencia del usuario',
				"paused-user-event": 'Impresora en pausa esperando al usuario',
				"tool0-cooled": 'Extrusora por debajo del umbral de temperatura especificado ({Tool0Threshold}°)',
				"tool0-warmed": 'Extrusora calentada a la temperatura especificada ({Tool0Threshold}°)',
				"palette2-error-while-printing": 'Error {PaletteError} en Palette 2. Su impresión ha sido suspendida',
				"layer_changed": 'Capa {PrintLayer}',
				"soc_temp_exceeded": 'Temperatura del SoC ({SoCTemp}°) por arriba de {SoCThreshold}°',
				"thermal-runaway": 'PELIGRO: ¡Posible fuga térmica detectada!'
			},
			'cs': {
				"Print complete": 'Tisk dokončen',
				"Print progress": "Vytištěno {PrintProgress}%",
				"bed-cooled": 'Teplota podložky pod nastavenou mezí ({BedThreshold}°)',
				"bed-warmed": 'Podložka nahřáta na nastavenou teplotu ({BedThreshold}°) a dobu ({Duration} minut)',
				"mmu-event": 'MMU vyžaduje asistenci uživatele',
				"paused-user-event": 'Tiskárna čeká na uživatele',
				"tool0-cooled": 'Tryska se ochladila na požadované teploty ({Tool0Threshold}°)',
				"tool0-warmed": 'Tryska se zahřeje na stanovenou teplotu ({Tool0Threshold}°)',
				"palette2-error-while-printing": 'Nastala chyba {PaletteError} na Palette 2. Tisk byl pozastaven',
				"layer_changed": 'Vrstva {PrintLayer}',
				"soc_temp_exceeded": 'Teplota SoC ({SoCTemp}°) přesahuje hranici {SoCThreshold}°',
				"thermal-runaway": 'NEBEZPEČÍ: Detekována možná ztráta teploty!'
			},
			'de': {
				"Print complete": 'Druck vollständig',
				"Print progress": "Fortschritt {PrintProgress}%",
				"bed-cooled": 'Druckbett unterhalb der vorgegebenen Temperaturschwelle ({BedThreshold}°)',
				"bed-warmed": 'Druckbett auf vorgegebene Temperatur ({BedThreshold}°) für gewählte Zeit aufgeheizt ({Duration} Minuten verstrichen)',
				"mmu-event": 'MMU fordert Hilfestellung',
				"paused-user-event": 'Drucker angehalten für Benutzer',
				"tool0-cooled": 'Extruder unterhalb der vorgegebenen Schwelle ({Tool0Threshold}°)',
				"tool0-warmed": 'Extruder auf spezifizierte Temperatur erwärmt ({Tool0Threshold}°)',
				"palette2-error-while-printing": 'Fehler {PaletteError} auf Palette 2 aufgetreten. Dein Druck wurde pausiert',
				"layer_changed": 'Schicht {PrintLayer}',
				"soc_temp_exceeded": 'SoC Temperatur ({SoCTemp}°) oberhalb der Schwelle {SoCThreshold}°',
				"thermal-runaway": 'GEFAHR: Möglichen thermischen Runaway erkannt!'
			},
			'it': {
				"Print complete": 'Stampa completata',
				"Print progress": "Avanzamento {PrintProgress}%",
				"bed-cooled": 'Piatto della stampante sotto la soglia di temperatura specificata ({BedThreshold}°)',
				"bed-warmed": 'Piatto della stampante riscaldato alla temperatura ({BedThreshold}°) e per la durata specificate ({Duration} minuti)',
				"mmu-event": 'MMU richiede l\'intervento dell\'utente',
				"paused-user-event": 'Stampante in pausa, in attesa dell\'utente',
				"tool0-cooled": 'Estensore sotto la soglia di temperatura specificata ({Tool0Threshold}°)',
				"tool0-warmed": 'Estensore riscaldato alla temperatura specificata ({Tool0Threshold}°)',
				"palette2-error-while-printing": 'Errore {PaletteError} su Palette 2. La tua stampa è in pausa',
				"layer_changed": 'Layer {PrintLayer}',
				"soc_temp_exceeded": 'Temperatura SoC ({SoCTemp}°) oltre la soglia di {SoCThreshold}°',
				"thermal-runaway": 'PERICOLO: è stato rilevata una possibile fuga termica (thermal runaway)!'
			},
			'lt-LT': {
				"Print complete": 'Baigta',
				"Print progress": "Progresas {PrintProgress}%",
				"bed-cooled": 'Paviršius atvėso ({BedThreshold}°)',
				"bed-warmed": 'Paviršius pasiekė nustatytą temperatūrą ({BedThreshold}°)',
				"mmu-event": 'MMU reikalauja pagalbos',
				"paused-user-event": 'Spausdintuvas laukia vartotojo',
				"tool0-cooled": 'Ekstruderis žemiau nurodytos temperatūros ribos ({Tool0Threshold}°)',
				"tool0-warmed": 'Ekstruderis pašildomas iki nurodytos temperatūros ({Tool0Threshold}°)',
				"palette2-error-while-printing": 'Klaida {PaletteError} ištiko Palette 2. Įjungta pauzė',
				"layer_changed": 'Sluoksnis {PrintLayer}',
				"soc_temp_exceeded": 'SoC temparatūra ({SoCTemp}°) virš ribos {SoCThreshold}°',
				"thermal-runaway": 'PAVOJUS! Galimai aptiktas temperatūros nuokrypis'
			},
			'nb': {
				"Print complete": 'Utskrift ferdig',
				"Print progress": "Fremdrift {PrintProgress}%",
				"bed-cooled": 'Skriveflate under spesifisert temperaturgrense ({BedThreshold}°)',
				"bed-warmed": 'Skriveflate varmet til spesifisert temperatur ({BedThreshold}°) og varighet ({Duration} minutter)',
				"mmu-event": 'MMU krever tilsyn',
				"paused-user-event": 'Skriver venter på bruker',
				"tool0-cooled": 'Ekstruder under spesifisert temperaturgrense ({Tool0Threshold}°)',
				"tool0-warmed": 'Ekstruder varmet opp til spesifisert temperatur ({Tool0Threshold}°)',
				"palette2-error-while-printing": 'Feil {PaletteError} oppstod på Palette 2. Din print er satt på pause',
				"layer_changed": 'Lag {PrintLayer}',
				"soc_temp_exceeded": 'SoC Temperatur ({SoCTemp}°) over terskelen {SoCThreshold}°',
				"thermal-runaway": 'FARE: Mulig termisk runaway oppdaget!'
			},
			'sv': {
				"Print complete": 'Utskrift klar',
				"Print progress": "Framsteg {PrintProgress}%",
				"bed-cooled": 'Skrivarbädd under angiven temperaturgräns ({BedThreshold}°)',
				"bed-warmed": 'Skrivarbädd uppvärmd till angiven temperatur ({BedThreshold}°) och varaktighet ({Duration} minuter)',
				"mmu-event": 'MMU kräver användarhjälp',
				"paused-user-event": 'Skrivare pausad för användare',
				"tool0-cooled": 'Extruder under angiven temperaturgräns ({Tool0Threshold}°)',
				"tool0-warmed": 'Extruder värms upp till specificerad temperatur ({Tool0Threshold}°)',
				"palette2-error-while-printing": 'Fel {PaletteError} inträffade på Palette 2. Din utskrift har pausats',
				"layer_changed": 'Lager {PrintLayer}',
				"soc_temp_exceeded": 'SoC-temperatur ({SoCTemp}°) över tröskeln {SoCThreshold}°',
				"thermal-runaway": 'VARNING: Möjlig skenande uppvärmning upptäckt!'
			},
			'fr': {
				"Print complete": 'Impression terminée',
				"Print progress": "Progression {PrintProgress}%",
				"bed-cooled": 'Température du plateau en dessous du seuil spécifié ({BedThreshold}°)',
				"bed-warmed": 'Plateau chauffé à la température ({BedThreshold}°) et durée spécifiées ({Duration} minutes écoulées)',
				"mmu-event": 'Le MMU demande une assistance',
				"paused-user-event": 'Imprimante en pause pour l’utilisateur',
				"tool0-cooled": 'Extrudeur en dessous du seuil spécifié ({Tool0Threshold}°)',
				"tool0-warmed": 'Extrudeuse chauffée à la température spécifiée ({Tool0Threshold}°)',
				"palette2-error-while-printing": 'Erreur {PaletteError} sur Palette 2. Impression en pause',
				"layer_changed": 'Layer {PrintLayer}',
				"soc_temp_exceeded": 'SoC Température ({SoCTemp}°) au-dessus du seuil {SoCThreshold}°',
				"thermal-runaway": 'DANGER: emballement thermique possible détecté !'
			},
			'ru': {
				"Print complete": 'Печать завершена',
				"Print progress": "Прогресс {PrintProgress}%",
				"bed-cooled": 'Температурный стола принтера ниже заданного порог ({BedThreshold}°)',
				"bed-warmed": 'Стол принтера нагревается до заданной температуры ({BedThreshold}°)',
				"mmu-event": 'MMU требуется помощь пользователя',
				"paused-user-event": 'Принтер приостановлен для пользователя',
				"tool0-cooled": 'Температурный порог экструдера ниже заданного ({Tool0Threshold}°)',
				"tool0-warmed": 'Экструдер нагрет до заданной температуры ({Tool0Threshold}°)',
				"palette2-error-while-printing": 'Произошла ошибка {PaletteError} в Palette 2. Печать была приостановлена',
				"layer_changed": 'Слой {PrintLayer}',
				"soc_temp_exceeded": 'Температура SoC ({SoCTemp}°) выше порога {SoCThreshold}°',
				"thermal-runaway": 'ОПАСНОСТЬ: Возможный термический бег выявлен!'
			},
			'nl': {
				"Print complete": 'Print compleet',
				"Print progress": "Voortgang {PrintProgress}%",
				"bed-cooled": 'Printerbed onder de opgegeven temperatuurdrempel ({BedThreshold}°)',
				"bed-warmed": 'Printerbed opgewarmd tot gespecificeerde temperatuur ({BedThreshold}°) en duur ({Duration} minuten verstreken)',
				"mmu-event": 'MMU vereist gebruikershulp',
				"paused-user-event": 'Printer is gepauzeerd voor gebruiker',
				"tool0-cooled": 'Extruder onder de opgegeven temperatuurdrempelwaarde ({Tool0Threshold}°)',
				"tool0-warmed": 'Extruder verwarmd tot gespecificeerde temperatuur ({Tool0Threshold}°)',
				"palette2-error-while-printing": 'Fout {PaletteError} heeft plaatsgevonden op palet 2. Uw afdruk is gepauzeerd',
				"layer_changed": 'Laag {PrintLayer}',
				"soc_temp_exceeded": 'SoC-temperatuur ({SoCTemp}°) boven drempel {SoCThreshold}°',
				"thermal-runaway": 'Gevaar: mogelijk thermal runaway gedecteerd!'
			},
			'zh-Hans': {
				"Print complete": '打印完成',
				"Print progress": "打印 {PrintProgress}％",
				"bed-cooled": '打印机床低于指定温度阈值 ({BedThreshold}°)',
				"bed-warmed": '打印机床加热到指定的温 ({BedThreshold}°) 度和持续时间 ({Duration} 分钟)',
				"mmu-event": 'MMU 需要用户协助',
				"paused-user-event": '打印机为用户暂停',
				"tool0-cooled": '挤出机低于指定温度阈值 ({Tool0Threshold}°)',
				"tool0-warmed": '挤出机加热到指定温度 ({Tool0Threshold}°)',
				"palette2-error-while-printing": '错误 {PaletteError} 发生在Palette 2 上。您的打印已暂停',
				"layer_changed": '{PrintLayer} 层',
				"soc_temp_exceeded": 'SoC 温度 ({SoCTemp}°) 高于阈值 {SoCThreshold}°',
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
			# Replace {} with specified parameter. Dictionary has to have corresponding keys or an error will be thrown.
			message = message.format(**event_param)

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
