import os
import json
import pytz
from datetime import datetime, date, time
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from django.test import TestCase
from selenium import webdriver
from hearthstone.enums import *
from hsreplaynet.api.models import UploadAgentAPIKey
from hsreplaynet.web.models import SingleSiteUploadToken


APP_DIR = os.path.dirname(os.path.abspath(__file__))
SCREEN_DUMP_LOCATION = os.path.join(APP_DIR, "screendumps")
JSON_DATA_LOCATION = os.path.join(APP_DIR, "json")
REPLAY_DATA_LOCATION = os.path.join(APP_DIR, "replays")
FIXTURE_DATA_LOCATION = os.path.join(APP_DIR, "fixtures")
LOG_DATA_LOCATION = os.path.join(APP_DIR, "logs")
INTEGRATION_DATA_LOCATION = os.path.join(APP_DIR, "integration_data")


class FunctionalTest(StaticLiveServerTestCase):
	def setUp(self):
		self.browser = webdriver.Firefox()
		self.browser.implicitly_wait(3)

	def get_json_fixture(self, name):
		name_with_extension = "%s.json" % name
		path = os.path.join(JSON_DATA_LOCATION, name_with_extension)
		if not os.path.exists(path):
			raise FileExistsError("Could not locate: %s" % path)

		return json.load(open(path))

	def tearDown(self):
		if self._test_has_failed():
			if not os.path.exists(SCREEN_DUMP_LOCATION):
				os.makedirs(SCREEN_DUMP_LOCATION)

			for ix, handle in enumerate(self.browser.window_handles):
				self._windowid = ix
				self.browser.switch_to.window(handle)
				self.take_screenshot()
				self.dump_html()
		self.browser.quit()
		super().tearDown()

	def _test_has_failed(self):
		for method, error in self._outcome.errors:
			if error:
				return True
		return False

	def take_screenshot(self):
		filename = self._get_filename() + ".png"
		print("screenshotting to", filename)
		self.browser.get_screenshot_as_file(filename)

	def dump_html(self):
		filename = self._get_filename() + ".html"
		print("dumping page HTML to", filename)
		with open(filename, "w") as f:
			f.write(self.browser.page_source)

	def _get_filename(self):
		timestamp = datetime.now().isoformat().replace(":", ".")[:19]
		return "{folder}/{classname}.{method}-window{windowid}-{timestamp}".format(
			folder = SCREEN_DUMP_LOCATION,
			classname = self.__class__.__name__,
			method = self._testMethodName,
			windowid = self._windowid,
			timestamp = timestamp
		)


class TestDataConsumerMixin:
	"""
	A mixin class for accessing test data.
	"""

	def get_raw_log_integration_fixtures(self):
		for test_case_uuid_dir in os.listdir(INTEGRATION_DATA_LOCATION):
			descriptor = json.load(open(os.path.join(INTEGRATION_DATA_LOCATION, test_case_uuid_dir, "descriptor.json")))
			raw_log = open(os.path.join(INTEGRATION_DATA_LOCATION, test_case_uuid_dir, "power.log")).read()
			yield (descriptor, raw_log, test_case_uuid_dir)

	def replay_file_path(self, replay_name):
		return os.path.join(REPLAY_DATA_LOCATION, replay_name)

	def read_raw_log_file(self, log_name):
		log_str = open(os.path.join(LOG_DATA_LOCATION, log_name)).read()
		return log_str.encode("utf-8")

	def get_raw_log_fixture_for_random_innkeeper_match(self):
		fixture = {}
		fixture["raw_log"] = self.read_raw_log_file("Power.log")
		utc = pytz.timezone("UTC")
		fixture["upload_date"] = datetime.combine(date.today(),
			time(hour=2, minute=59, second=14, microsecond=608862, tzinfo=utc)
		)

		fixture["match_start_timestamp"] = fixture["upload_date"]
		fixture["match_end_timestamp"] = datetime.combine(date.today(),
			time(hour=3, minute=0, second=50, microsecond=723960, tzinfo=utc)
		)

		fixture["num_turns"] = 6
		fixture["num_entities"] = 70

		return fixture


class CardDataBaseTest(TestCase):
	@classmethod
	def setUpClass(cls):
		# Call `manage.py load_cards`
		call_command("load_cards")
		super(CardDataBaseTest, cls).setUpClass()


def create_agent_and_token():
	agent = UploadAgentAPIKey.objects.create(
		full_name="Test Upload Agent",
		email="test@testagent.example.org",
		website="http://testagent.example.org"
	)
	token = SingleSiteUploadToken.objects.create()
	agent.tokens.add(token)

	return agent, token
