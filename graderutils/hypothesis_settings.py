"""
Hypothesis settings.
"""

# from hypothesis import HealthCheck

# Customized settings for specified exercise tests
HYPOTHESIS = {
    "all": {
        "max_examples": 100, # Number of test values
        "database": None, # Hypothesis database
        "max_shrinks": 1, # How many times the dataset is shrinked when a test fails
        # "suppress_health_check": [HealthCheck.too_slow] # Keep running tests even if data generation is slow
    },
    "sorting": {
        "max_examples": 10
    },
    "bst_remove": {
        "max_examples": 50
    },
    "network": {
        "max_examples": 200
    }
}
# The hypothesis database allows dataset generation to continue from the
# previous failed values.
# It's set to None here because the MOOC grader destroys its sandboxes after each
# grading task. So the hypothesis database would be deleted also.
# You can read more about the hypothesis example database here:
# https://hypothesis.readthedocs.io/en/latest/database.html

def update_settings_profile(test_key, settings):
    """
    Updates an imported settings module with predefined settings.

    @type test_key: C{str}
    @param test_key: Settings key for a specific test settings defined in HYPOTHESIS.
    @type settings: hypothesis.settings module
    @param settings: Settings which are being overridden.
    """
    custom_settings = HYPOTHESIS["all"].copy()

    if test_key in HYPOTHESIS.keys() and test_key != "all":
        custom_settings.update(HYPOTHESIS[test_key])

    # As of 07/2016 hypothesis does not seem to provide loading custom settings
    # without first registering a profile and then loading the same profile
    settings.register_profile(test_key, settings(**custom_settings))
