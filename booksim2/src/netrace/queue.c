/*
 * Copyright (c) 2010-2011 The University of Texas at Austin
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "queue.h"

queue_t* queue_new() {
	queue_t* to_return = (queue_t*) malloc( sizeof(queue_t) );
	if( to_return == NULL ) {
		printf( "Failed malloc in queue_new\n" );
		exit(0);
	}
	to_return->head = NULL;
	to_return->tail = NULL;
	return to_return;
}

void queue_delete( queue_t* q ) {
	void* elem;
	while( ! queue_empty( q ) ) {
		elem = queue_pop_front( q );
		free( elem );
	}
	free( q );
}

int queue_empty( queue_t* q ) {
	return (q == NULL) || (q->head == NULL);
}

void queue_push_back( queue_t* q, void* e ) {
	if( q != NULL ) {
		if( q->head == NULL ) {
			q->head = (node_t*) malloc( sizeof(node_t) );
			if( q->head == NULL ) {
				printf( "Failed malloc in queue_push_back\n" );
				exit(0);
			}
			q->tail = q->head;
			q->head->prev = NULL;
			q->head->next = NULL;
			q->head->elem = e;
			q->head->prio = 0;
		} else {
			q->tail->next = (node_t*) malloc( sizeof(node_t) );
			if( q->head == NULL ) {
				printf( "Failed malloc in queue_push_back\n" );
				exit(0);
			}
			q->tail->next->prev = q->tail;
			q->tail = q->tail->next;
			q->tail->next = NULL;
			q->tail->elem = e;
			q->tail->prio = q->tail->prev->prio;
		}
	} else {
		printf( "Must initialize queue with queue_new()\n" );
		exit(0);
	}
}

void queue_push( queue_t* q, void* e, unsigned long long int prio ) {
	if( q != NULL ) {
		if( q->head == NULL ) {
			q->head = (node_t*) malloc( sizeof(node_t) );
			if( q->head == NULL ) {
				printf( "Failed malloc in queue_push\n" );
				exit(0);
			}
			q->tail = q->head;
			q->head->prev = NULL;
			q->head->next = NULL;
			q->head->elem = e;
			q->head->prio = prio;
		} else {
			node_t* to_add = (node_t*) malloc( sizeof(node_t) );
			if( to_add == NULL ) {
				printf( "Failed malloc in queue_push\n" );
				exit(0);
			}
			to_add->prio = prio;
			to_add->elem = e;
			node_t* behind;
			for( behind = q->head; (behind != NULL) && (behind->prio < prio); behind = behind->next );
			to_add->next = behind;
			if( behind == NULL ) {
				to_add->prev = q->tail;
				q->tail->next = to_add;
				q->tail = to_add;
			} else if( behind == q->head ) {
				to_add->prev = behind->prev;
				behind->prev = to_add;
				q->head = to_add;
			} else {
				to_add->prev = behind->prev;
				to_add->prev->next = to_add;
				behind->prev = to_add;
			}
		}
	} else {
		printf( "Must initialize queue with queue_new()\n" );
		exit(0);
	}
}

void* queue_peek_front( queue_t* q ) {
	if( (q != NULL) && (q->head != NULL) ) {
		return q->head->elem;
	} else {
		return NULL;
	}
}

void* queue_pop_front( queue_t* q ) {
	void* to_return = NULL;
	if( (q != NULL) && (q->head != NULL) ) {
		to_return = q->head->elem;
		node_t* temp = q->head;
		q->head = q->head->next;
		if( q->head == NULL ) {
			q->tail = NULL;
		}
		free( temp );
	}
	return to_return;
}

void queue_remove( queue_t* q, void* e ) {
	if( q != NULL ) {
		node_t* temp = q->head;
		while( temp != NULL ) {
			if( temp->elem == e ) {
				if( temp->prev == NULL ) {
					if( temp->next == NULL ) {
						q->head = NULL;
						q->tail = NULL;
					} else {
						q->head = temp->next;
						temp->next->prev = NULL;
					}
				} else {
					temp->prev->next = temp->next;
					if( temp->next != NULL ) {
						temp->next->prev = temp->prev;
					} else {
						q->tail = temp->prev;
					}
				}
				free( temp );
				temp = NULL;
			} else {
				temp = temp->next;
			}
		}
	}
}

