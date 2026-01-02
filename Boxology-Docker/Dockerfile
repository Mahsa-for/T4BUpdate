FROM fjudith/draw.io

COPY ./js/plugins/BoxologyValidation.js /usr/local/tomcat/webapps/draw/plugins/BoxologyValidation.js

COPY ./lib/PatternLib.xml /usr/local/tomcat/webapps/draw/lib/PatternLib.xml
COPY ./lib/ShapeLib.xml /usr/local/tomcat/webapps/draw/lib/ShapeLib.xml
COPY ./lib/AnnotationLib.xml /usr/local/tomcat/webapps/draw/lib/AnnotationLib.xml

COPY ./images/sidebar-pattern.png /usr/local/tomcat/webapps/draw/images/sidebar-pattern.png
COPY ./images/sidebar-shape.png /usr/local/tomcat/webapps/draw/images/sidebar-shape.png
COPY ./images/sidebar-annotation.png /usr/local/tomcat/webapps/draw/images/sidebar-annotation.png

# Copy docker-entrypoint
<<<<<<< HEAD
COPY docker-entrypoint.sh /docker-entrypoint.sh
=======
COPY docker-entrypoint.sh /
>>>>>>> d412e9492b4f17941c6fbde5de5dd2d9b4daf85a
RUN chmod +x /docker-entrypoint.sh
CMD ["copy","catalina.sh", "run"]


