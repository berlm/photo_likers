## What is it?

This is the experimental django-application for efficient sorting 
and filtering 10^6 likable photos labeled by 100 tags with possibility of 
specifying several tags that must me included and excluded, 
and sorting either by the number of likes or the creation date. 

## How to run it on a local machine?

* Clone the repository
```
$ git clone git@github.com:berlm/photo_likers.git
```
* Install requirements
```
$ pip install -r requirements.txt
```
* Create an empty MySQL (or other) database and configure either 
the DATABASE_URL environment variable to point to your database 
or configure it directly in ./PhotoLikers/settings.py. By default 
it connects to MySQL database named photo_likers on localhost:3060.

Depending on your database install python package for working with this database,
e.g. mysql-python or mysqlclient for MySQL.
 
* Create models of application
```
$ python manage.py migrate
```
* Create superuser 
```
$ python manage.py createsuperuser
```
* (optional) Run ./photo_likers/sample_data.py to fill your database with 
10^6 sample liked and tagged photo's urls. 
```
$ python ./photo_likers/sample_data.py
```
* Run server 
```
$ python manage.py runserver
```
* Try [Sample page](http://127.0.0.1:8000/photos/sort=0&tags=&page=1), 
 choose parameters and enjoy :)
* Remarks: 
The application utilize in-memory caches to efficiently 
acquire requested page. By default, the "Tag"-caches are loaded asynchronously 
after running server. For 10^6 photos and 100 tags it may take few minutes 
to load the cache and if some required cache is not loaded when the 
page is requested, it is loaded on the page request. So it may take some 
time to upload a page for the first request for chosen tags and sort type.
The behaviour can be changed to synchronous in photo_likers/settings.py 

In the case of using only pagination without changing chosen tags and 
sorting type another cache is used to optimize search. Therefore repeated 
requests during 10min. for chosen tags and the sorting type must perform 
in less than a second.  
