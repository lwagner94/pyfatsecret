"""
    fatsecret
    ---------

    Simple python wrapper of the Fatsecret API

"""

import datetime

from rauth.service import OAuth1Service


# FIXME add method to set default units and make it an optional argument to the constructor
class Fatsecret:
    """
    Session for API interaction

    Can have an unauthorized session for access to public data or a 3-legged Oauth authenticated session
    for access to Fatsecret user profile data

    Fatsecret only supports OAuth 1.0 with HMAC-SHA1 signed requests.

    """

    def __init__(self, consumer_key, consumer_secret, session_token=None):
        """ Create unauthorized session or open existing authorized session

        :param consumer_key: App API Key. Register at http://platform.fatsecret.com/api/
        :type consumer_key: str
        :param consumer_secret: Secret app API key
        :type consumer_secret: str
        :param session_token: Access Token / Access Secret pair from existing authorized session
        :type session_token: tuple
        """

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

        # Needed for new access. Generated by running get_authorize_url()
        self.request_token = None
        self.request_token_secret = None

        # Required for accessing user info. Generated by running authenticate()
        self.access_token = None
        self.access_token_secret = None

        self.oauth = OAuth1Service(
            name='fatsecret',
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            request_token_url='http://www.fatsecret.com/oauth/request_token',
            access_token_url='http://www.fatsecret.com/oauth/access_token',
            authorize_url='http://www.fatsecret.com/oauth/authorize',
            base_url='http://platform.fatsecret.com/rest/server.api')

        # Open prior session or default to unauthorized session
        if session_token:
            self.access_token = session_token[0]
            self.access_token_secret = session_token[1]
            self.session = self.oauth.get_session(token=session_token)
        else:
            # Default to unauthorized session
            self.session = self.oauth.get_session()

    @property
    def api_url(self):

        return 'http://platform.fatsecret.com/rest/server.api'

    def get_authorize_url(self, callback_url='oob'):
        """ URL used to authenticate app to access Fatsecret User data

        If no callback url is provided then you'll need to allow the user to enter in a PIN that Fatsecret
        displays once access was allowed by the user

        :param callback_url: An absolute URL to redirect the User to when they have completed authentication
        :type callback_url: str
        """
        self.request_token, self.request_token_secret = \
            self.oauth.get_request_token(method='GET', params={'oauth_callback': callback_url})

        return self.oauth.get_authorize_url(self.request_token)

    def authenticate(self, verifier):
        """ Retrieve access tokens once user has approved access to authenticate session

        :param verifier: PIN displayed to user or returned by authorize_url when callback url is provided
        :type verifier: int
        :param user_id: Can authenticate with user id
        :type user_id: str
        """

        session_token = self.oauth.get_access_token(self.request_token, self.request_token_secret,
                                                    params={'oauth_verifier': verifier})

        self.access_token = session_token[0]
        self.access_token_secret = session_token[1]
        self.session = self.oauth.get_session(session_token)

        # Return session token for app specific caching
        return session_token

    def close(self):
        """Session cleanup"""
        self.session.close()

    @staticmethod
    def unix_time(dt):

        epoch = datetime.datetime.utcfromtimestamp(0)
        delta = dt - epoch
        return delta.days

    @staticmethod
    def valid_response(response):
        """Helper function to check JSON response for errors

        :param response: JSON response from API call
        :type response: dict
        """
        if response.json():

            for key in response.json():

                # Error Code Handling
                if key == 'error':
                    code = response.json()[key]['code']
                    message = response.json()[key]['message']
                    if code == 2:
                        raise AuthenticationError(2, "This api call requires an authenticated session")

                    elif code in [1, 10, 11, 12, 20, 21]:
                        raise GeneralError(code, message)

                    elif 3 <= code <= 9:
                        raise AuthenticationError(code, message)

                    elif 101 <= code <= 108:
                        raise ParameterError(code, message)

                    elif 201 <= code <= 207:
                        raise ApplicationError(code, message)

                # All other response options
                elif key == 'success':
                    return True

                elif key == 'foods':
                    return response.json()[key]['food']

                elif key == 'recipes':
                    return response.json()[key]['recipe']

                elif key == 'saved_meals':
                    return response.json()[key]['saved_meal']

                elif key == 'saved_meal_items':
                    return response.json()[key]['saved_meal_item']

                elif key == 'exercise_types':
                    return response.json()[key]['exercise']

                elif key == 'food_entries':
                    return response.json()[key]['food_entry']

                elif key == 'month':
                    return response.json()[key]['day']

                elif key == 'profile':
                    if 'auth_token' in response.json()[key]:
                        return response.json()[key]['auth_token'], response.json()[key]['auth_secret']
                    else:
                        return response.json()[key]

                elif key in ('food', 'recipe', 'recipe_types', 'saved_meal_id', 'saved_meal_item_id', 'food_entry_id'):
                    return response.json()[key]

    def food_add_favorite(self, food_id, serving_id=None, number_of_units=None):
        """ Add a food to a user's favorite according to the parameters specified.

        :param food_id: The ID of the favorite food to add.
        :param serving_id: Only required if number_of_units is present. This is the ID of the favorite serving.
        :param number_of_units: Only required if serving_id is present. This is the favorite number of servings.
        """

        params = {'method': 'food.add_favorite', 'format': 'json', 'food_id': food_id}

        if serving_id and number_of_units:
            params['serving_id'] = serving_id
            params['number_of_units'] = number_of_units

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_delete_favorite(self, food_id, serving_id=None, number_of_units=None):
        """ Delete the food to a user's favorite according to the parameters specified.

        :param food_id: The ID of the favorite food to add.
        :param serving_id: Only required if number_of_units is present. This is the ID of the favorite serving.
        :param number_of_units: Only required if serving_id is present. This is the favorite number of servings.
        """

        params = {'method': 'food.delete_favorite', 'format': 'json', 'food_id': food_id}

        if serving_id and number_of_units:
            params['serving_id'] = serving_id
            params['number_of_units'] = number_of_units

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_get(self, food_id):
        """Returns detailed nutritional information for the specified food.

        Use this call to display nutrition values for a food to users.

        :param food_id: Fatsecret food identifier
        :type food_id: str
        """

        params = {'method': 'food.get', 'food_id': food_id, 'format': 'json'}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def foods_get_favorites(self):
        """Returns the favorite foods for the authenticated user."""

        params = {'method': 'foods.get_favorites', 'format': 'json'}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def foods_get_most_eaten(self, meal=None):
        """ Returns the most eaten foods for the user according to the meal specified.

        :param meal: 'breakfast', 'lunch', 'dinner', or 'other'
        :type meal: str
        """
        params = {'method': 'foods.get_most_eaten', 'format': 'json'}

        if meal in ['breakfast', 'lunch', 'dinner', 'other']:
            params['meal'] = meal

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def foods_get_recently_eaten(self, meal=None):
        """ Returns the recently eaten foods for the user according to the meal specified

        :param meal: 'breakfast', 'lunch', 'dinner', or 'other'
        :type meal: str
        """
        params = {'method': 'foods.get_recently_eaten', 'format': 'json'}

        if meal in ['breakfast', 'lunch', 'dinner', 'other']:
            params['meal'] = meal

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def foods_search(self, search_expression, page_number=None, max_results=None):
        """Conducts a search of the food database using the search expression specified.

        The results are paginated according to a zero-based "page" offset. Successive pages of results
        may be retrieved by specifying a starting page offset value. For instance, specifying a max_results
        of 10 and page_number of 4 will return results numbered 41-50.

        :param search_expression: term or phrase to search
        :type search_expression: str
        :param page_number: page set to return (default 0)
        :type page_number: int
        :param max_results: total results per page (default 20)
        :type max_results: int
        """
        params = {'method': 'foods.search', 'search_expression': search_expression, 'format': 'json'}

        if page_number and max_results:
            params['page_number'] = page_number
            params['max_results'] = max_results

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def recipes_add_favorite(self, recipe_id):
        """ Add a recipe to a user's favorite.

        :param recipe_id: The ID of the favorite recipe to add.
        """

        params = {'method': 'recipes.add_favorites', 'format': 'json', 'recipe_id': recipe_id}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def recipes_delete_favorite(self, recipe_id):
        """ Delete a recipe to a user's favorite.

        :param recipe_id: The ID of the favorite recipe to delete.
        """

        params = {'method': 'recipes.delete_favorites', 'format': 'json', 'recipe_id': recipe_id}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def recipe_get(self, recipe_id):
        """Returns detailed information for the specified recipe.

        :param recipe_id: Fatsecret ID of desired recipe
        :type recipe_id: str
        """

        params = {'method': 'recipe.get', 'format': 'json', 'recipe_id': recipe_id}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def recipes_get_favorites(self):
        """Returns the favorite recipes for the specified user."""

        params = {'method': 'recipes.get_favorites', 'format': 'json'}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def recipes_search(self, search_expression, recipe_type=None, page_number=None, max_results=None):
        """ Conducts a search of the recipe database using the search expression specified.

        The results are paginated according to a zero-based "page" offset. Successive pages of results may be
        retrieved by specifying a starting page offset value. For instance, specifying a max_results of 10 and
        page_number of 4 will return results numbered 41-50.

        :param search_expression: phrase to search on
        :type search_expression: str
        :param recipe_type: type of recipe to filter
        :type recipe_type: str
        :param page_number: result page to return (default 0)
        :type page_number: int
        :param max_results: total results per page to return (default 20)
        :type max_results: int
        """

        params = {'method': 'recipes.search', 'search_expression': search_expression, 'format': 'json'}

        if recipe_type:
            params['recipe_type'] = recipe_type
        if page_number and max_results:
            params['page_number'] = page_number
            params['max_results'] = max_results

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def recipe_types_get(self):
        """ This is a utility method, returning the full list of all supported recipe type names. """

        params = {'method': 'recipe_types.get', 'format': 'json'}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def saved_meal_create(self, meal_name, meal_desc=None, meals=None):
        """ Records a saved meal for the user according to the parameters specified.

        :param meal_name: The name of the saved meal.
        :type meal_name: str
        :param meal_desc: A short description of the saved meal.
        :type meal_desc: str
        :param meals: A comma separated list of the types of meal this saved meal is suitable for.
            Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :type meals: list
        """

        params = {'method': 'saved_meal.create', 'format': 'json', 'saved_meal_name': meal_name}
        if meal_desc:
            params['saved_meal_description'] = meal_desc
        if meals:
            params['meals'] = ",".join(meals)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def saved_meal_delete(self, meal_id):
        """ Deletes the specified saved meal for the user.

        :param meal_id: The ID of the saved meal to delete.
        :type meal_id: str
        """

        params = {'method': 'saved_meal.delete', 'format': 'json', 'saved_meal_id': meal_id}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def saved_meal_edit(self, meal_id, new_name=None, meal_desc=None, meals=None):
        """ Records a change to a user's saved meal.

        :param meal_id: The ID of the food entry to edit.
        :param new_name: The new name of the saved meal.
        :param meal_desc: The new description of the saved meal.
        :param meals: The new comma separated list of the types of meal this saved meal is suitable for.
            Valid meal types are "breakfast", "lunch", "dinner" and "other".
        """

        params = {'method': 'saved_meal.edit', 'format': 'json', 'saved_meal_id': meal_id}

        if new_name:
            params['saved_meal_name'] = new_name
        if meal_desc:
            params['saved_meal_description'] = meal_desc
        if meals:
            params['meals'] = ",".join(meals)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def saved_meal_get(self, meal=None):
        """ Returns saved meals for the authenticated user

        :param meal: Filter result set to 'Breakfast', 'Lunch', 'Dinner', or 'Other'
        :type meal: str
        """

        params = {'method': 'saved_meals.get', 'format': 'json'}

        if meal:
            params['meal'] = meal

        response = self.session.get(self.api_url, params)
        return self.valid_response(response)

    def saved_meal_item_add(self, meal_id, food_id, food_entry_name, serving_id, num_units):
        """ Adds a food to a user's saved meal according to the parameters specified.

        :param meal_id: The ID of the saved meal.
        :param food_id: The ID of the food to add to the saved meal.
        :param food_entry_name: The name of the food to add to the saved meal.
        :param serving_id: The ID of the serving of the food to add to the saved meal.
        :param num_units: The number of servings of the food to add to the saved meal.
        """
        params = {'method': 'saved_meal_item.add', 'format': 'json', 'saved_meal_id': meal_id,
                  'food_id': food_id, 'food_entry_name': food_entry_name, 'serving_id': serving_id,
                  'number_of_units': num_units}

        response = self.session.get(self.api_url, params)
        return self.valid_response(response)

    def saved_meal_item_delete(self, meal_item_id):
        """ Deletes the specified saved meal item for the user.

        :param meal_item_id: The ID of the saved meal item to delete.
        :type meal_item_id: str
        """

        params = {'method': 'saved_meal_item.delete', 'format': 'json', 'saved_meal_item_id': meal_item_id}

        response = self.session.get(self.api_url, params)
        return self.valid_response(response)

    def saved_meal_item_edit(self, meal_item_id, item_name=None, num_units=None):
        """ Records a change to a user's saved meal item.

        Note that the serving_id of the saved meal item may not be adjusted, however one or more of the other
        remaining properties – saved_meal_item_name or number_of_units may be altered. In order to adjust a
        serving_id for which a saved_meal_item was recorded the original item must be deleted and a new item recorded.

        :param meal_item_id: The ID of the saved meal item to edit.
        :type meal_item_id: str
        :param item_name: The new name of the saved meal item.
        :type item_name: str
        :param num_units: The new number of servings of the saved meal item.
        :type num_units: float
        """

        params = {'method': 'saved_meal_item.edit', 'format': 'json', 'saved_meal_item_id': meal_item_id}

        if item_name:
            params['saved_meal_item_name'] = item_name
        if num_units:
            params['number_of_units'] = num_units

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def saved_meal_items_get(self, meal_id):
        """ Returns saved meal items for a specified saved meal.

        :param meal_id: The ID of the saved meal to retrieve the saved_meal_items for.
        :type meal_id: str
        """

        params = {'method': 'saved_meal_items.get', 'format': 'json', 'saved_meal_id': meal_id}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def exercises_get(self):
        """ This is a utility method, returning the full list of all supported exercise type names and
        their associated unique identifiers.
        """

        params = {'method': 'exercises.get', 'format': 'json'}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def profile_create(self, user_id=None):
        """ Creates a new profile and returns the oauth_token and oauth_secret for the new profile.

        The token and secret returned by this method are persisted indefinitely and may be used in order to
        provide profile-specific information storage for users including food and exercise diaries and weight tracking.

        :param user_id: You can set your own ID for the newly created profile if you do not wish to store the
            auth_token and auth_secret. Particularly useful if you are only using the FatSecret JavaScript API.
            Use profile.get_auth to retrieve auth_token and auth_secret.
        :type user_id: str
        """

        params = {'method': 'profile.create', 'format': 'json'}

        if user_id:
            params['user_id'] = user_id

        response = self.session.get(self.api_url, params=params)

        return self.valid_response(response)

    def profile_get(self):
        """ Returns general status information for a nominated user. """

        params = {'method': 'profile.get', 'format': 'json'}
        response = self.session.get(self.api_url, params=params)

        return self.valid_response(response)

    def profile_get_auth(self, user_id):
        """ Returns the authentication information for a nominated user.

        :param user_id: The user_id specified in profile.create.
        """

        params = {'method': 'profile.get_auth', 'format': 'json', 'user_id': user_id}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entries_copy(self, from_date, to_date, meal=None):
        """ Copies the food entries for a specified meal from a nominated date to a nominated date.

        :param from_date: The date to copy food entries from
        :type from_date: datetime
        :param to_date: The date to copy food entries to (default value is the current day).
        :type to_date: datetime
        :param meal: The type of meal to copy. Valid meal types are "breakfast", "lunch", "dinner" and "other"
            (default value is all).
        :type meal: str
        """

        params = {'method': 'food_entries.copy', 'format': 'json',
                  'from_date': self.unix_time(from_date), 'to_date': self.unix_time(to_date)}

        if meal:
            params['meal'] = meal

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entries_copy_saved_meal(self, meal_id, meal, date=None):
        """ Copies the food entries for a specified saved meal to a specified meal.

        :param meal_id: The ID of the saved meal
        :param meal: The type of meal eaten. Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :param date: The number of days since January 1, 1970 (default value is the current day).
        :type date: datetime
        """

        params = {'method': 'food_entries.copy_saved_meal', 'format': 'json',
                  'saved_meal_id': meal_id, 'meal': meal}

        if date:
            params['date'] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entries_get(self, food_entry_id=None, date=None):
        """ Returns saved food diary entries for the user according to the filter specified.

        This method can be used to return all food diary entries recorded on a nominated date or a single food
        diary entry with a nominated food_entry_id.

        :: You must specify either date or food_entry_id.

        :param food_entry_id: The ID of the food entry to retrieve. You must specify either date or food_entry_id.
        :param date: The number of days since January 1, 1970 (default value is the current day).
        """

        params = {'method': 'food_entries.get', 'format': 'json'}

        if food_entry_id:
            params['food_entry_id'] = food_entry_id
        elif date:
            params['date'] = self.unix_time(date)
        else:
            return  # exit without running as no valid parameter was provided

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entries_get_month(self, date=None):
        """ Returns summary daily nutritional information for a user's food diary entries for the month specified.

        Use this call to display nutritional information to users about their food intake for a nominated month.

        :param date: The number of days since January 1, 1970 (default value is the current day).
        """

        params = {'method': 'food_entries.get_month', 'format': 'json'}

        if date:
            params['date'] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entry_create(self, food_id, food_entry_name, serving_id, number_of_units, meal, date=None):
        """ Records a food diary entry for the user according to the parameters specified.

        :param food_id: The ID of the food eaten.
        :param food_entry_name: The name of the food entry.
        :param serving_id: The ID of the serving
        :param number_of_units: The number of servings eaten.
        :param meal: The type of meal eaten. Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :param date: The number of days since January 1, 1970 (default value is the current day).
        """

        params = {'method': 'food_entry.create', 'format': 'json', 'food_id': food_id,
                  'food_entry_name': food_entry_name, 'serving_id': serving_id, 'number_of_units': number_of_units,
                  'meal': meal}

        if date:
            params['date'] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entry_delete(self, food_entry_id):
        """ Deletes the specified food entry for the user.

        :param food_entry_id: The ID of the food entry to delete.
        """

        params = {'method': 'food_entry.delete', 'format': 'json', 'food_entry_id': food_entry_id}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entry_edit(self, food_entry_id, entry_name=None, serving_id=None, num_units=None, meal=None):
        """ Adjusts the recorded values for a food diary entry.

        Note that the date of the entry may not be adjusted, however one or more of the other remaining
        properties – food_entry_name, serving_id, number_of_units, or meal may be altered. In order to shift
        the date for which a food diary entry was recorded the original entry must be deleted and a new entry recorded.

        :param food_entry_id: The ID of the food entry to edit.
        :param entry_name: The new name of the food entry.
        :param serving_id: The new ID of the serving to change to.
        :param num_units: The new number of servings eaten.
        :param meal: The new type of meal eaten. Valid meal types are "breakfast", "lunch", "dinner" and "other".
        """

        params = {'method': 'food_entry.edit', 'food_entry_id': food_entry_id, 'format': 'json'}

        if entry_name:
            params['food_entry_name'] = entry_name

        if serving_id:
            params['serving_id'] = serving_id

        if num_units:
            params['number_of_units'] = num_units

        if meal:
            params['meal'] = meal

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def exercises_entries_commit_day(self, date=None):
        """ Saves the default exercise entries for the user on a nominated date.

        :param date: The number of days since January 1, 1970 (default value is the current day).
        """

        params = {'method': 'exercises_entries.commit_day', 'format': 'json'}

        if date:
            params['date'] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def exercises_entries_get(self, date=None):
        """ Returns the daily exercise entries for the user on a nominated date.

        The API will always return 24 hours worth of exercise entries for a given user on a given date.
        These entries will either be "template" entries (which a user may override for any given day of the week)
        or saved exercise entry values.

        :param date: The number of days since January 1, 1970 (default value is the current day).
        """

        params = {'method': 'exercises_entries.get', 'format': 'json'}

        if date:
            params['date'] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def exercise_entries_get_month(self, date=None):
        """ Returns the summary estimated daily calories expended for a user's exercise diary entries for
        the month specified. Use this call to display total energy expenditure information to users about their
        exercise and activities for a nominated month.

        :param date: The number of days since January 1, 1970 (default value is the current day).
        """

        params = {'method': 'exercises_entries.get_month', 'format': 'json'}

        if date:
            params['date'] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def exercise_entries_save_template(self, days, date=None):
        """ Takes the set of exercise entries on a nominated date and saves these entries as "template"
        entries for nominated days of the week.

        :param days: The days of the week specified as bits with Sunday being the 1st bit and Saturday being the
            last and then converted to an Int. For example Tuesday and Thursday would be represented as 00010100 in
            bits or 20 in Int where Tuesday is the 3rd bit from the right and Thursday being the 5th.
            Must be between 0 and 128.
        :param date: The number of days since January 1, 1970 (default value is the current day).
        """
        params = {'method': 'exercises_entries.get_month', 'format': 'json', 'days': int(days)}

        if date:
            params['date'] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def exercise_entry_edit(self, shift_to_id, shift_from_id, minutes, date=None, shift_to_name=None,
                            shift_from_name=None, kcals=None):
        """ Records a change to a user's exercise diary entry for a nominated date.

        All changes to an exercise diary involve either increasing the duration of an existing activity or
        introducing a new activity for a nominated duration. Because there are always 24 hours worth of exercise
        entries on any given date, the user must nominate the exercise or activity from which the time was taken
        to balance out the total duration of activities and exercises for the 24 hour period. As such, each change
        to the exercise entries on a given day is a "shifting" operation where time is moved from one activity to
        another. An exercise is removed from the day when all of the time allocated to it is shifted to other exercises.

        :param shift_to_id: The ID of the exercise type to shift to.
        :param shift_from_id: The ID of the exercise type to shift from.
        :param minutes: The number of minutes to shift.
        :param date: The number of days since January 1, 1970 (default value is the current day).
        :param shift_to_name: Only required if shift_to_id is 0 (exercise type "Other").
            This is the name of the new custom exercise type to shift to.
        :param shift_from_name: Only required if shift_from_id is 0 (exercise type "Other").
            This is the name of the custom exercise type to shift from.
        """

        params = {'method': 'exercise_entry.edit', 'format': 'json', 'shift_to_id': shift_to_id,
                  'shift_from_id': shift_from_id, 'minutes': minutes}

        if date:
            params['date'] = self.unix_time(date)

        if shift_to_id == 0:
            if shift_to_name:
                params['shift_to_name'] = shift_to_name
            elif kcals:
                params['kcals'] = kcals
            else:
                return
        if shift_from_id == 0:
            if shift_from_name:
                params['shift_from_name'] = shift_from_name
            else:
                return

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def weight_update(self, current_weight_kg, date=None, weight_type='kg', height_type='cm', goal_weight_kg=None,
                      current_height_cm=None, comment=None):
        """ Records a user's weight for a nominated date.

        First time weigh-ins require the goal_weight_kg and current_height_cm parameters.

        :param current_weight_kg: The current weight of the user in kilograms.
        :param date: The number of days since January 1, 1970 (default value is the current day).
        :param weight_type: The weight measurement type for this user profile. Valid types are "kg" and "lb"
        :param height_type: The height measurement type for this user profile. Valid types are "cm" and "inch"
        :param goal_weight_kg: The goal weight of the user in kilograms. This is required for the first weigh-in.
        :param current_height_cm: The current height of the user in centimetres. This is required for the first
            weigh-in. You can only set this for the first time (subsequent updates will not change a user's height)
        :param comment: A comment for this weigh-in.
        """

        params = {'method': 'weight.update', 'format': 'json', 'current_weight_kg': current_weight_kg,
                  'weight_type': weight_type, 'height_type': height_type}

        if date:
            params['date'] = self.unix_time(date)
        if goal_weight_kg:
            params['goal_weight_kg'] = goal_weight_kg
        if current_height_cm:
            params['current_height_cm'] = current_height_cm
        if comment:
            params['comment'] = comment

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def weights_get_month(self, date=None):
        """ Returns the recorded weights for a user for the month specified. Use this call to display a user's
        weight chart or log of weight changes for a nominated month.

        :param date: The number of days since January 1, 1970 (default value is the current day).
        """

        params = {'method': 'weights.get_month', 'format': 'json'}

        if date:
            params['date'] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)


class BaseFatsecretError(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, "Error {0}: {1}".format(code, message))


class GeneralError(BaseFatsecretError):
    def __init__(self, code, message):
        BaseFatsecretError.__init__(self, code, message)


class AuthenticationError(BaseFatsecretError):
    def __init__(self, code, message):
        BaseFatsecretError.__init__(self, code, message)


class ParameterError(BaseFatsecretError):
    def __init__(self, code, message):
        BaseFatsecretError.__init__(self, code, message)


class ApplicationError(BaseFatsecretError):
    def __init__(self, code, message):
        BaseFatsecretError.__init__(self, code, message)
