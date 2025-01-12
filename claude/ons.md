Search for:Search

* * *

- [Robert Grant](https://digitalblog.ons.gov.uk/author/robertgrant)
- February 15, 2021

Categories: [API](https://digitalblog.ons.gov.uk/category/api/)

### Introduction

Over the past 12 months we’ve had a lot of interest from our users about accessing our data [via our Beta API](https://api.beta.ons.gov.uk/v1/datasets) to build automated charts, apps and tools.

A group from Cambridge University [built a coronavirus deaths tracker](https://wintoncentre.maths.cam.ac.uk/coronavirus/covid-excess/) using our Beta service. In July 2020 ONS published a [subnational ageing tool](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/articles/subnationalageingtool/2020-07-20) that also uses this service.

We have data on a variety of topics available, covering the likes of inflation, unemployment and well-being. More are added regularly.

This post introduces our Beta service, focusing on the API and goes into detail about how users can get the most out of it.

### What is the ONS Beta service?

Our Beta service is called Customise My Data (CMD). It takes data we publish at ONS and makes it available in a more open, useful format for our users. It runs alongside our regular publications via our [release calendar](https://www.ons.gov.uk/releasecalendar).

CMD comes in two parts: the filter journey and the Application Programming Interface (API).

For example, let’s say you’re interested to know the number of people aged in their thirties in Cardiff. You can use [our population filter](https://www.ons.gov.uk/datasets/mid-year-pop-est/editions/mid-2019-april-2020-geography/versions/2) to generate a custom spreadsheet with [just that data filtered for you](https://www.ons.gov.uk/filter-outputs/6e9ccdd5-dad9-44c0-b746-1883f51a9c7d) to download in a XLS or CSV file.

For users with no particular background in programming this is likely to be the best way for you to access CMD. A good place to dive into our data is via [our local statistics page](https://www.ons.gov.uk/help/localstatistics), scrolling down to the datasets listed under ‘Customise My Data’.

Our API is a system that allows users to make more advanced requests for this same data.

It’s designed for more technically-minded users who want data in a consistent, structured format. You can use a variety of tools and programs to work with our API data, such as Python, JavaScript and R.

Access to the API is free with no registration required. It returns data in a JSON format. There are some rate limits: please see the Frequently Asked Questions at the bottom of this post.

For users who just want to filter and access data quickly, with no special technical knowledge, please try filtering the datasets through your browser.

### Getting started with the API

Our [datasets endpoint](https://api.beta.ons.gov.uk/v1/datasets) lists all the datasets we have available on the beta API.

We will take Consumer Prices Index including owner occupiers’ housing costs (CPIH) as an example dataset and walk through it.

Navigating to the [CPIH dataset endpoint](https://api.beta.ons.gov.uk/v1/datasets/cpih01) will return some JSON metadata that tells you some relevant information about the dataset such as the `release_frequency` (monthly) and the

`next_release` (17 February 2021 at the time of writing).

All datasets on the API have at least one edition and one version. A version is an update to the data, usually the next release in a time series.

An edition contains all the versions that fit together. We may have to start a new edition if there is a significant change to the data structure such as a change in geography or a revision to an official classification.

We can see from the [editions endpoint](https://api.beta.ons.gov.uk/v1/datasets/cpih01/editions) for CPIH that it has just one edition called

`time-series`. This `time-series` has a `latest_version` which at the time of writing was number 4.

### How data is structured in the API

Before we start to query the data itself it will help to understand how data is structured in the API.

Data is held in a [tidy data format](https://cran.r-project.org/web/packages/tidyr/vignettes/tidy-data.html). This means:

- Each observation (or value) is a row in the dataset.
- Each variable (also known as a dimension) is a column in the dataset.

All datasets in the API have a time and a geography dimension plus one or more additional dimensions.

In the CPIH example the time is a range of months stretching (currently) from 1988 to 2021 and just one geography: United Kingdom. We also have an `aggregate` dimension that contains the various goods and services covered in the dataset. To make a request for data users must specify an option from all the dimensions in a dataset.

### How to query the API

There are three ways to query the ONS API:

1. Download the entire dataset.
2. Query an observation.
3. Filter a dataset for more advanced queries.

To download the entire CPIH dataset, navigate to the `latest_version`. [From here](https://api.beta.ons.gov.uk/v1/datasets/cpih01/editions/time-series/versions/4) you will see the CSV or XLS download link. You can read it directly into a program such as Python or paste the URL into a web browser to download it automatically.

The second way to query the API is the observations endpoint. This allows you to query an observation or several observations of data. To write our query we will need to know what dimensions are contained within the CPIH dataset and select at least one option from each.

To do this, take the `latest_version` URL and add `/dimensions`.

[This will show you](https://api.beta.ons.gov.uk/v1/datasets/cpih01/editions/time-series/versions/4/dimensions) a list of dimensions included in this data. In our case we have three:

1. Time
2. Geography
3. Aggregate

To find out what options are available for each dimension, choose one and add it to your request, followed by `/options`. For example, [here are all the valid time options](https://api.beta.ons.gov.uk/v1/datasets/cpih01/editions/time-series/versions/4/dimensions/time/options) for this dataset.

Pick an observation you want and save it. Once you have observations for all dimensions, you can put them together using the [observations endpoint](https://api.beta.ons.gov.uk/v1/datasets/cpih01/editions/time-series/versions/4/observations). This can be found by putting `/observations` after the `latest_version`.

A [valid observation query](https://api.beta.ons.gov.uk/v1/datasets/cpih01/editions/time-series/versions/4/observations?time=Apr-20&geography=K02000001&aggregate=cpih1dim1G100000) therefore looks like this:

```
https://api.beta.ons.gov.uk/v1/datasets/cpih01/editions/time-series/versions/
4/observations?time=Apr-20&geography=K02000001&aggregate=cpih1dim1G100000
```

This will return an observation of 117.5.

You also have the ability to use one wildcard operator `*` in your call. This will return all options for that dimension. This call returns all months covered by time for this aggregate:

```
https://api.beta.ons.gov.uk/v1/datasets/cpih01/editions/time-series/versions/
4/observations?time=*&geography=K02000001&aggregate=cpih1dim1G100000
```

Please note that the wildcard operator is limited to one dimension per dataset.

If you require larger slices of data there is a more advanced ‘filter a dataset’ functionality. This requires POST requests rather than the GET requests we have been covering in this article. Please see the [developer documentation](https://developer.ons.gov.uk/tour/getting-started/) for more details.

### Frequently Asked Questions (FAQs)

#### When is the API updated?

The API is updated as soon as possible after publication of the same data on the main [ONS release calendar](https://www.ons.gov.uk/releasecalendar). Currently we don’t have the ability to publish the data simultaneously at 07:00 or 09:30 along with our bulletins. There is a time lag that varies from dataset to dataset, which we aim to keep to a minimum.

**Are there any limits on API use?**

Yes. Use of the API is limited to 120 requests per 10 seconds and 200 requests per minute. Any traffic above this limit will be blocked for one minute and then allowed to continue. In this case the user will see a JSON response 429 HTTP error code and a `Retry-After` header showing the number of seconds until the user may continue.

We also have some limits on the number of items returned for certain endpoints and an offset parameter to navigate these limits. Please see the [full developer documentation](https://developer.ons.gov.uk/) for more details.

#### Why isn’t the data I want available?

All data published on CMD has to be assessed for its suitability, processed, reformatted and signed off, which takes time. We are always working on adding new datasets. If there are any you would like to be made available please get in touch with us via customise.my.data@ons.gov.uk.

#### Do you have a sub-national breakdown of data available via this service?

Yes – please see [the ONS local statistics page](https://www.ons.gov.uk/help/localstatistics) and scroll down to ‘Customise my data (beta website)’.

#### How can I get in touch with you about this service?

Please email customise.my.data@ons.gov.uk.

#### Is there more technical documentation available?

Yes, please see our full [developer docs](https://developer.ons.gov.uk/tour/getting-started/).

Tags: [API](https://digitalblog.ons.gov.uk/tag/api/), [Customise My Data](https://digitalblog.ons.gov.uk/tag/customise-my-data/)

[A story of two content designers in 2020](https://digitalblog.ons.gov.uk/2021/02/05/a-story-of-two-content-designers-in-2020/)

[Publishing with the Integrated Data Programme](https://digitalblog.ons.gov.uk/2021/03/11/publishing-with-the-integrated-data-programme/)

### Share this post

- [Twitter](https://twitter.com/intent/tweet?original_referer&url=https%3A%2F%2Fdigitalblog.ons.gov.uk%2F2021%2F02%2F15%2Fhow-to-access-data-from-the-ons-beta-api%2F&text=How+to+access+data+from+the+ONS+beta+API)
- [Facebook](https://www.facebook.com/sharer/sharer.php?u=https%3A%2F%2Fdigitalblog.ons.gov.uk%2F2021%2F02%2F15%2Fhow-to-access-data-from-the-ons-beta-api%2F)
- [LinkedIn](https://www.linkedin.com/shareArticle?url=https%3A%2F%2Fdigitalblog.ons.gov.uk%2F2021%2F02%2F15%2Fhow-to-access-data-from-the-ons-beta-api%2F)
- [Email](mailto:?subject=I wanted to share this post with you from ONS Digital&body=How to access data from the ONS beta API https://digitalblog.ons.gov.uk/2021/02/15/how-to-access-data-from-the-ons-beta-api/)