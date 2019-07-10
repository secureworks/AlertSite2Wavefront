# Alertsite to Wavefront

This python script sends alertsite monitoring results to wavefront. This allows you to monitor availability and performance of the [Alertsite](https://smartbear.com/product/alertsite/overview/) checks in [Wavefront](https://www.wavefront.com/) (and combine alertsite data with other data monitored by wavefront).

# How does it operate?

Every 30 seconds it:
* Gets its configuration from config.json
* Connects to [Alertsite report API](https://support.smartbear.com/alertsite/docs/api/report-api/sitestatus-report.html) which retrieves the latest status of all checks from all locations they are checked from: 
* Parses the XML response for each check at each location. Fields:
    * display_descrip - alertsite check name
    * last_status - alertsite status (0 = success, etc [Alertsite code documentation](https://support.smartbear.com/alertsite/docs/appendixes/status-codes.html))
    * Sets status to 1 if successful
    * Sets status to 0 if not successful
    * Ignores the entry if the last check indicates a problem at alertsite (vs a problem with our system)
    * dt_last_status - timestamp for check
    * resptime_last - seconds in response time for check
* Stores them in a dictionary, only storing the most recent one (as we don't want to send all data to wavefront, just the most recent)
* Loads the last set of results from a file stored from the last run
* Iterates through the dictionary and checks to see which ones are newer that what was sent to wavefront last time
* Sends each to the wavefront proxy : [Wavefront data format](https://docs.wavefront.com/wavefront_data_format.html).
    * Format: alertsite.(alertsitecheckname).(status|seconds) metricvalue timestamp source=alertsite
* Saves the current dictionary in a file (to use in the next run)
