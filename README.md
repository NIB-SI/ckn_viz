## CKN model exporation

This is a flask application which implements visual exploration of the CKN network. It implements interactive node search (several data fields can be indexed), simple editing of selected nodes, and nice interactive visualization of the resulting network.


### Requirements

-  docker
-  docker-compose


### How to run

The following command

```sh
$ docker-compose up --build
```

will build the images and run the container. The application is now available for testing at [http://localhost:5005](http://localhost:5005).

### Deployment

The `docker-compose.prod.yml` configuration file is ready to be used in production. By default, the application is served on port 8080 but this can be changed if needed.

###  Authors

[Vid Podpečan](vid.podpecan@ijs.si)


### License

MIT
