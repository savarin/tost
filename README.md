*This project was completed as a part of Bradfield's API class, September 2018.*

tost
====

tost is a text snippets RESTful API with a capability-based permissions model.

### Components

* tost - server API
* tost-client - client library
* tost-cli - command line interface
* tost-web - web interface


### License

This project is licensed under the MIT License.


### Example

    $ tost signup alice@example.com
    > signing you up ...
    > done. you have been emailed an access token
    
    $ tost signup alice@example.com
    > that email address has already signed up, search your email for an auth token
    
    $ tost list
    > you have not signed in
    > run: tost signin <<auth token that was emailed to you>>
    
    $ tost signin alice@example.com foo
    > signing you in ...
    > incorrect auth token
    
    $ tost signin alice@example.com 4561e50a
    > signing you in ...
    > done
    
    $ tost signin bob@example.com 6a503ca1
    > signing you up ...
    > done
    # bob is granted access to alice's tost simply by learning the id (grant) alice uses to access the document
    
    $ tost show e7aa3f47
    > downloading ...
    > id: 43076e69
    2017Q3 projections
    profits: up
    costs: down
    # he gets his own grant
    
    $ tost list
    430         
    2017Q3 projections         
    by: alice@example.com
    # alice learns that bob has accessed the tost
    
    $ tost signin alice@example.com 4561e50a
    > signing you in ...
    > done
    $ tost list
    e7a
    2017Q3 projections
    [1 grant]
    
    $ tost grants e7a
    bob@example.com
    # ... time passes, more grants are issued ...
    
    $ tost grants e7a
    bob@example.com
    carol@example.com
    daniel@example.com
    eloise@example.com
    
    $ tost grants e7a revoke daniel@example.com
    > revoking access for daniel@example.com ...
    > done. access for the following downstream users was also revoked:
    > eloise@example.com