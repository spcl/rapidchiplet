CC			= gcc
CFLAGS		= -Wall -O3 -c -g
LDFLAGS         += -lm
ifdef ver
	ifeq "$(ver)" "debug"
		CFLAGS += -DDEBUG_ON
	endif
endif
SOURCES		= netrace.c queue.c main.c
OBJECTS		= $(SOURCES:.c=.o)
EXECUTABLE	= main

all: $(SOURCES) $(EXECUTABLE)

$(EXECUTABLE): $(OBJECTS)
	$(CC) $(LDFLAGS) $(INCLUDES) $(LIBRARIES) $(OBJECTS) -o $(EXECUTABLE) $(LIBS) $(LDFLAGS)

.o: $(SOURCES)
	$(CC) $(CFLAGS) $(INCLUDES) $(LIBRARIES) $< -o $@ $(LIBS)

.c:
	$(CC) $(CFLAGS) $(INCLUDES) $(LIBRARIES) $< -o $@ $(LIBS)

clean:
	rm -f $(EXECUTABLE) *.o
