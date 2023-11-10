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

#include "netrace.h"

char*				nt_input_popencmd;
FILE*				nt_input_tracefile;
char*				nt_input_buffer;
nt_header_t*		nt_input_trheader;
int					nt_dependencies_off;
int					nt_self_throttling;
int					nt_primed_self_throttle;
int					nt_done_reading;
unsigned long long int nt_latest_active_packet_cycle;
nt_dep_ref_node_t** nt_dependency_array;
unsigned long long int nt_num_active_packets;
const char* nt_packet_types[] = { "InvalidCmd", "ReadReq", "ReadResp",
				"ReadRespWithInvalidate", "WriteReq", "WriteResp",
				"Writeback", "InvalidCmd", "InvalidCmd", "InvalidCmd",
				"InvalidCmd", "InvalidCmd", "InvalidCmd", "UpgradeReq",
				"UpgradeResp", "ReadExReq", "ReadExResp", "InvalidCmd",
				"InvalidCmd", "InvalidCmd", "InvalidCmd", "InvalidCmd",
				"InvalidCmd", "InvalidCmd", "InvalidCmd", "BadAddressError",
				"InvalidCmd", "InvalidateReq", "InvalidateResp",
				"DowngradeReq", "DowngradeResp" };

int nt_packet_sizes[] = { /*InvalidCmd*/ -1, /*ReadReq*/ 8, /*ReadResp*/ 72,
				/*ReadRespWithInvalidate*/ 72, /*WriteReq*/ 72, /*WriteResp*/ 8,
				/*Writeback*/ 72, /*InvalidCmd*/ -1, /*InvalidCmd*/ -1, /*InvalidCmd*/ -1,
				/*InvalidCmd*/ -1, /*InvalidCmd*/ -1, /*InvalidCmd*/ -1, /*UpgradeReq*/ 8,
				/*UpgradeResp*/ 8, /*ReadExReq*/ 8, /*ReadExResp*/ 72, /*InvalidCmd*/ -1,
				/*InvalidCmd*/ -1, /*InvalidCmd*/ -1, /*InvalidCmd*/ -1, /*InvalidCmd*/ -1,
				/*InvalidCmd*/ -1, /*InvalidCmd*/ -1, /*InvalidCmd*/ -1, /*BadAddressError*/ 8,
				/*InvalidCmd*/ -1, /*InvalidateReq*/ 8, /*InvalidateResp*/ 8,
				/*DowngradeReq*/ 8, /*DowngradeResp*/ 72 };

const char* nt_node_types[] = { "L1 Data Cache", "L1 Instruction Cache",
				"L2 Cache", "Memory Controller", "Invalid Node Type" };

nt_packet_list_t*	nt_cleared_packets_list;
nt_packet_list_t*	nt_cleared_packets_list_tail;
int nt_track_cleared_packets_list;

void nt_open_trfile( const char* trfilename ) {
	nt_close_trfile();
	int i;
	int length = 20;

	nt_latest_active_packet_cycle = 0;
	nt_done_reading = 0;

	for( i = 0; trfilename[i] != 0; i++, length++ );
	nt_input_popencmd = (char*) nt_checked_malloc( length * sizeof(char) );
	sprintf( nt_input_popencmd, "bzip2 -dc %s", trfilename );
	nt_input_tracefile = popen( nt_input_popencmd, "r" );
	if( nt_input_tracefile == NULL ) {
		nt_error( "failed to open pipe to trace file" );
	}
	nt_input_trheader = nt_read_trheader();
	if( nt_dependency_array == NULL ) {
		nt_dependency_array = nt_checked_malloc( sizeof(nt_dep_ref_node_t*) * NT_DEPENDENCY_ARRAY_SIZE );
		memset( nt_dependency_array, 0, sizeof(nt_dep_ref_node_t*) * NT_DEPENDENCY_ARRAY_SIZE );
		nt_num_active_packets = 0;
	} else {
		nt_error( "dependency array not NULL on file open" );
	}
}

nt_header_t* nt_read_trheader() {

	#pragma pack(push,1)
	struct nt_header_pack {
		unsigned int nt_magic;
		float version;
		char benchmark_name[NT_BMARK_NAME_LENGTH];
		unsigned char num_nodes;
		unsigned char pad;
		unsigned long long int num_cycles;
		unsigned long long int num_packets;
		unsigned int notes_length;  // Includes null-terminating char
		unsigned int num_regions;
		char padding[8];
	};
	#pragma pack(pop)

	int err = 0;
	char strerr[180];

	// Read Header
	struct nt_header_pack* in_header = nt_checked_malloc( sizeof(struct nt_header_pack) );
	fseek( nt_input_tracefile, 0, SEEK_SET );
	if( (err = fread( in_header, sizeof(struct nt_header_pack), 1, nt_input_tracefile )) < 0 ) {
		sprintf( strerr, "failed to read trace file header: err = %d", err );
		nt_error( strerr );
	}

	// Copy data from struct to header
	nt_header_t* to_return = (nt_header_t*) nt_checked_malloc( sizeof(nt_header_t) );
	memset( to_return, 0, sizeof(nt_header_t) );
	to_return->nt_magic = in_header->nt_magic;
	to_return->version = in_header->version;
	strcpy( to_return->benchmark_name, in_header->benchmark_name );
	to_return->num_nodes = in_header->num_nodes;
	to_return->num_cycles = in_header->num_cycles;
	to_return->num_packets = in_header->num_packets;
	to_return->notes_length = in_header->notes_length;
	to_return->num_regions = in_header->num_regions;
	free( in_header );

	// Error Checking
	if( to_return->nt_magic != NT_MAGIC ) {
		if( nt_little_endian() != 1 ) {
			nt_error( "only little endian architectures are currently supported" );
		} else {
			nt_error( "invalid trace file: bad magic" );
		}
	}
	if( to_return->version != 1.0f ) {
		sprintf( strerr, "trace file is unsupported version: %f", to_return->version );
		nt_error( strerr );
	}
	// Read Rest of Header
	if( to_return->notes_length > 0 && to_return->notes_length < 8192 ) {
		to_return->notes = (char*) nt_checked_malloc( to_return->notes_length * sizeof(char) );
		if( (err = fread( to_return->notes, sizeof(char), to_return->notes_length, nt_input_tracefile )) < 0 ) {
			sprintf( strerr, "failed to read trace file header notes: err = %d\n", err );
			nt_error( strerr );
		}
	} else {
		to_return->notes = NULL;
	}
	if( to_return->num_regions > 0 ) {
		if( to_return->num_regions <= 100 ) {
			to_return->regions = (nt_regionhead_t*) nt_checked_malloc( to_return->num_regions * sizeof(nt_regionhead_t) );
			if( (err = fread( to_return->regions, sizeof(nt_regionhead_t), to_return->num_regions, nt_input_tracefile )) < 0 ) {
				sprintf( strerr, "failed to read trace file header regions: error = %d\n", err );
				nt_error( strerr );
			}
		} else {
			nt_error( "lots of regions... is this correct?" );
		}
	} else {
		to_return->regions = NULL;
	}
	return to_return;
}

void nt_disable_dependencies() {
	if( nt_track_cleared_packets_list ) {
		nt_error( "Cannot turn off dependencies when tracking cleared packets list" );
	}
	nt_dependencies_off = 1;
}

void nt_seek_region( nt_regionhead_t* region ) {
	int err = 0;
	char strerr[180];
	if( nt_input_tracefile != NULL ) {
		if( region != NULL ) {
			// Clear all existing dependencies
			nt_delete_all_dependencies();
			// Reopen file to fast-forward to region
			// fseek doesn't work on compressed file
			pclose( nt_input_tracefile );
			nt_input_tracefile = popen( nt_input_popencmd, "r" );
            unsigned long long int seek_offset = nt_get_headersize() + region->seek_offset;
            unsigned long long int read_length = 4096;
			char* buffer = (char*) nt_checked_malloc( read_length );
			while( seek_offset > read_length ) {
				if( (err = fread( buffer, 1, read_length, nt_input_tracefile )) < 0 ) {
					sprintf( strerr, "failed to seek region: error = %d\n", err );
					nt_error( strerr );
				}
				seek_offset -= read_length;
			}
			if( (err = fread( buffer, 1, seek_offset, nt_input_tracefile )) < 0 ) {
				sprintf( strerr, "failed to seek region: error = %d\n", err );
				nt_error( strerr );
			}
			free( buffer );
			if( nt_self_throttling ) {
				// Prime the pump to read in self throttled packets
				nt_prime_self_throttle();
			}
		} else {
			nt_error( "invalid region passed: NULL" );
		}
	} else {
		nt_error( "must open trace file with nt_open_trfile before seeking" );
	}
}

nt_packet_t* nt_read_packet( void ) {

	// printf("START nt_read_packet\n");
	#pragma pack(push,1)
	struct nt_packet_pack {
		unsigned long long int cycle;
		unsigned int id;
		unsigned int addr;
		unsigned char type;
		unsigned char src;
		unsigned char dst;
		unsigned char node_types;
		unsigned char num_deps;
	};
	#pragma pack(pop)

	int err = 0;
	unsigned int i;
	char strerr[180];
	nt_packet_t* to_return = NULL;
	if( nt_input_tracefile != NULL ) {
		to_return = nt_packet_malloc();
		if( (err = fread( to_return, 1, sizeof(struct nt_packet_pack), nt_input_tracefile )) < 0 ) {
			sprintf( strerr, "failed to read packet: err = %d", err );
			nt_error( strerr );
		}
		if( err > 0 && err < sizeof(struct nt_packet_pack) ) {
			// Bad packet - end of file
			nt_error( "unexpectedly reached end of trace file - perhaps corrupt" );
		} else if( err == 0 ) {
			// End of file
			free( to_return );
			to_return = NULL;
			return to_return;
		}
		if( !nt_dependencies_off ) {
			// Track dependencies: add to_return to dependencies array
			nt_dep_ref_node_t* node_ptr = nt_get_dependency_node( to_return->id );
			if( node_ptr == NULL ) {
				node_ptr = nt_add_dependency_node( to_return->id );
			}
			node_ptr->node_packet = to_return;
		}
		nt_num_active_packets++;
		nt_latest_active_packet_cycle = to_return->cycle;
		if( to_return->num_deps == 0 ) {
			to_return->deps = NULL;
		} else {
			to_return->deps = nt_dependency_malloc( to_return->num_deps );
			if( (err = fread( to_return->deps, sizeof(nt_dependency_t), to_return->num_deps, nt_input_tracefile )) < 0 ) {
				sprintf( strerr, "failed to read dependencies: err = %d", err );
				nt_error( strerr );
			}
			if( !nt_dependencies_off ) {
				// Track dependencies: add to_return downward dependencies to array
				for( i = 0; i < to_return->num_deps; i++ ) {
					unsigned int dep_id = to_return->deps[i];
					nt_dep_ref_node_t* node_ptr = nt_get_dependency_node( dep_id );
					if( node_ptr == NULL ) {
						node_ptr = nt_add_dependency_node( dep_id );
					}
					node_ptr->ref_count++;
				}
			}
		}
	} else {
		nt_error( "must open trace file with nt_open_trfile before reading" );
	}
	return to_return;
}

nt_dep_ref_node_t* nt_add_dependency_node( unsigned int packet_id ) {
	if( nt_dependency_array != NULL ) {
		unsigned int index = packet_id % NT_DEPENDENCY_ARRAY_SIZE;
		nt_dep_ref_node_t* dep_ptr = nt_dependency_array[index];
		if( dep_ptr == NULL ) {
			nt_dependency_array[index] = nt_checked_malloc( sizeof(nt_dep_ref_node_t) );
			dep_ptr = nt_dependency_array[index];
		} else {
			for( ; dep_ptr->next_node != NULL; dep_ptr = dep_ptr->next_node );
			dep_ptr->next_node = nt_checked_malloc( sizeof(nt_dep_ref_node_t) );
			dep_ptr = dep_ptr->next_node;
		}
		dep_ptr->node_packet = NULL;
		dep_ptr->packet_id = packet_id;
		dep_ptr->ref_count = 0;
		dep_ptr->next_node = NULL;
		return dep_ptr;
	} else {
		nt_error( "dependency array NULL on node addition" );
	}
	return NULL;
}

void nt_read_ahead( unsigned long long int current_cycle ) {
	// printf("START read ahead\n");
	unsigned long long int read_to_cycle = current_cycle + NT_READ_AHEAD;
	if( read_to_cycle < current_cycle ) {
		nt_error( "trying to read too far ahead... overflowed :(" );
	}
	if( read_to_cycle > nt_latest_active_packet_cycle ) {
		nt_packet_t* packet;
		while( nt_latest_active_packet_cycle <= read_to_cycle && !nt_done_reading ) {
			packet = nt_read_packet();
			if( packet == NULL ) {
				// This is the exit condition... how do we signal it to the
				// network simulator? We shouldn't need to... It is tracking
				// whether there are packets in flight.
				// Just in case, we'll provide this global indicator
				nt_done_reading = 1;
			} else if( nt_dependencies_cleared( packet ) ) {
				nt_add_cleared_packet_to_list( packet );
			//} else {
				// Ignore this packet, since the reader is already tracking it
			}
		}
	}
}

nt_packet_t* nt_remove_dependency_node( unsigned int packet_id ) {
	if( nt_dependency_array != NULL ) {
		unsigned int index = packet_id % NT_DEPENDENCY_ARRAY_SIZE;
		nt_dep_ref_node_t* dep_ptr = nt_dependency_array[index];
		if( dep_ptr == NULL ) {
			return NULL;
		} else {
			nt_dep_ref_node_t* prev_ptr = NULL;
			for( ; dep_ptr != NULL; prev_ptr = dep_ptr, dep_ptr = dep_ptr->next_node ) {
				if( dep_ptr->packet_id == packet_id ) break;
			}
			if( dep_ptr == NULL ) {
				return NULL;
			}
			if( prev_ptr == NULL ) {
				nt_dependency_array[index] = dep_ptr->next_node;
			} else {
				prev_ptr->next_node = dep_ptr->next_node;
			}
			nt_packet_t* packet = dep_ptr->node_packet;
			free( dep_ptr );
			return packet;
		}
	} else {
		nt_error( "dependency array NULL on node remove" );
	}
	return NULL;
}

nt_dep_ref_node_t* nt_get_dependency_node( unsigned int packet_id ) {
	if( nt_dependency_array != NULL ) {
		unsigned int index = packet_id % NT_DEPENDENCY_ARRAY_SIZE;
		nt_dep_ref_node_t* dep_ptr;
		for( dep_ptr = nt_dependency_array[index]; dep_ptr != NULL; dep_ptr = dep_ptr->next_node ) {
			if( dep_ptr->packet_id == packet_id ) break;
		}
		return dep_ptr;
	} else {
		nt_error( "dependency array not NULL on node search" );
	}
	return NULL;
}

int nt_dependencies_cleared( nt_packet_t* packet ) {
	if( nt_input_tracefile != NULL ) {
		nt_dep_ref_node_t* node_ptr = nt_get_dependency_node( packet->id );
		if( node_ptr == NULL || nt_dependencies_off ) {
			return 1;
		} else {
			return (node_ptr->ref_count == 0);
		}
	} else {
		nt_error( "must open trace file with nt_open_trfile before injecting" );
	}
	return 1;
}

void nt_clear_dependencies_free_packet( nt_packet_t* packet ) {
	unsigned int i;
	// printf("clear start\n");
	if( nt_input_tracefile != NULL ) {
		if( packet != NULL ) {
			// If self-throttling, read ahead in the trace file
			// to ensure that there are new packets ready to go
			if( nt_self_throttling ) {
				nt_read_ahead( packet->cycle );
			}
			for( i = 0; i < packet->num_deps; i++ ) {
				unsigned int dep_id = packet->deps[i];
				nt_dep_ref_node_t* node_ptr = nt_get_dependency_node( dep_id );
				if( node_ptr == NULL ) {
					if( !nt_dependencies_off ) {
						// TODO: check if this is a problem with short seeks
						nt_print_packet( packet );
						nt_error( "failed to find dependency node" );
					}
				} else {
					if( node_ptr->ref_count == 0 ) {
						nt_error( "invalid reference count on node while decrementing" );
					}
					node_ptr->ref_count--;
					if( nt_track_cleared_packets_list ) {
						if( node_ptr->ref_count == 0 ) {
							// This test alleviates the possibility of a packet
							// having ref_count zero before it has been read
							// from the trace (node_packet = NULL)
							if( node_ptr->node_packet ) {
								// printf("clear 1\n");
								// nt_get_cleared_packets_list();
								nt_add_cleared_packet_to_list( node_ptr->node_packet );
								// nt_get_cleared_packets_list();
								// printf("\n");
								// printf("clear 2\n");
							}
						}
					}
				}
			}
			nt_remove_dependency_node( packet->id );
			nt_packet_free( packet );
			nt_num_active_packets--;
		}
	} else {
		nt_error( "must open trace file with nt_open_trfile before ejecting" );
	}
}

void nt_init_cleared_packets_list() {
	if( nt_dependencies_off ) {
		nt_error( "Cannot return cleared packets list when dependencies are turned off" );
	}
	nt_track_cleared_packets_list = 1;
	nt_cleared_packets_list = NULL;
	nt_cleared_packets_list_tail = NULL;
}

void nt_init_self_throttling() {
	if( nt_dependencies_off ) {
		nt_error( "Cannot self throttle packets when dependencies are turned off" );
	}
	nt_self_throttling = 1;
	nt_primed_self_throttle = 0;
	nt_init_cleared_packets_list();
}

nt_packet_list_t* nt_get_cleared_packets_list() {
	if( !nt_primed_self_throttle ) {
		nt_prime_self_throttle();
	}
	// if(nt_cleared_packets_list == NULL) { printf("netrace.c: nt_cleared_packets_list IS NULL\n"); } else { printf("netrace.c: nt_cleared_packets_list IS NOT NULL\n"); }
	return nt_cleared_packets_list;
}

void nt_prime_self_throttle() {
	nt_packet_t* packet = nt_read_packet();
	if( nt_dependencies_cleared( packet ) ) {
		// printf("nt_prime_self_throttle\n");
		nt_add_cleared_packet_to_list( packet );
	}
	nt_primed_self_throttle = 1;
	// printf("%llu", packet->cycle);
	// printf("SEE abovee \n");
	nt_read_ahead( packet->cycle );
}

void nt_add_cleared_packet_to_list( nt_packet_t* packet ) {
	nt_packet_list_t* new_node = nt_checked_malloc( sizeof(nt_packet_list_t) );
	new_node->node_packet = packet;
	new_node->next = NULL;
	if( nt_cleared_packets_list == NULL ) {
		// printf("if1\n");
		nt_cleared_packets_list = nt_cleared_packets_list_tail = new_node;
	} else {
		// printf("else1\n");
		nt_cleared_packets_list_tail->next = new_node;
		nt_cleared_packets_list_tail = new_node;
	}
}

void nt_empty_cleared_packets_list() {
	// printf("netrace.c: nt_cleared_packets_list -> NULL\n");

	while( nt_cleared_packets_list != NULL ) {
		nt_packet_list_t* temp = nt_cleared_packets_list;
		nt_cleared_packets_list = nt_cleared_packets_list->next;
		free( temp );
	}
	nt_cleared_packets_list = nt_cleared_packets_list_tail = NULL;
}

void nt_close_trfile() {
	if( nt_input_tracefile != NULL ) {
		pclose( nt_input_tracefile );
		nt_input_tracefile = NULL;
		nt_free_trheader( nt_input_trheader );
		if( nt_input_popencmd != NULL ) {
			free( nt_input_popencmd );
		}
		nt_input_popencmd = NULL;
		nt_delete_all_dependencies();
		free(nt_dependency_array);
		nt_dependency_array = NULL;
	}
}

void nt_delete_all_dependencies() {
	int i;
	for( i = 0; i < NT_DEPENDENCY_ARRAY_SIZE; i++ ) {
		while( nt_dependency_array[i] != NULL ) {
			nt_remove_dependency_node( nt_dependency_array[i]->packet_id );
		}
	}
}

void nt_print_header( nt_header_t* header ) {
	unsigned int i;
	if( header != NULL ) {
		printf( "NT_TRACEFILE---------------------\n" );

		printf( "  Benchmark: %s\n", header->benchmark_name );
		printf( "  Magic Correct? %s\n", (header->nt_magic == NT_MAGIC) ? "TRUE" : "FALSE" );
		printf( "  Tracefile Version: v%1.1f\n", header->version );
		printf( "  Number of Program Regions: %d\n", header->num_regions );
		printf( "  Number of Simulated Nodes: %d\n", header->num_nodes );
		printf( "  Simulated Cycles: %lld\n", header->num_cycles );
		printf( "  Simulated Packets: %lld\n", header->num_packets );
		printf( "  Average injection rate: %f\n", (double)header->num_packets / (double)header->num_cycles );
		if( header->notes_length > 0 ) {
			printf( "  Notes: %s\n", header->notes );
		}

		for( i = 0; i < header->num_regions; i++ ) {
			printf( "    Region %d:\n", i );
			printf( "      Seek Offset: %lld\n", header->regions[i].seek_offset );
			printf( "      Simulated Cycles: %lld\n", header->regions[i].num_cycles );
			printf( "      Simulated Packets: %lld\n", header->regions[i].num_packets );
			printf( "      Average injection rate: %f\n", (double)header->regions[i].num_packets / (double)header->regions[i].num_cycles );
			printf( "      Average injection rate per node: %f\n", (double)header->regions[i].num_packets / (double)header->regions[i].num_cycles / (double)header->num_nodes );
		}
		printf( "  Size of header (B): %u\n", nt_get_headersize() );
		printf( "NT_TRACEFILE---------------------\n" );
	} else {
		printf( "NULL header passed to nt_print_header\n" );
	}
}

void nt_print_trheader() {
	nt_print_header( nt_input_trheader );
}

nt_header_t* nt_get_trheader() {
	if( nt_input_tracefile != NULL ) {
		return nt_input_trheader;
	} else {
		nt_error( "must open trace file with nt_open_trfile before header is available" );
	}
	return NULL;
}

float nt_get_trversion() {
	if( nt_input_tracefile != NULL ) {
		return nt_input_trheader->version;
	} else {
		nt_error( "must open trace file with nt_open_trfile before version is available" );
	}
	return 0.0f;
}

nt_packet_t* nt_packet_malloc() {
	// TODO: v1.1?
	// Allocate large array (1+ pages) to reduce # system calls
	return (nt_packet_t*) nt_checked_malloc( sizeof(nt_packet_t) );
}

nt_dependency_t* nt_dependency_malloc( unsigned char num_deps ) {
	// TODO: v1.1?
	// Allocate large array (1+ pages) to reduce # system calls
	return (nt_dependency_t*) nt_checked_malloc( num_deps * sizeof(nt_dependency_t) );
}

int nt_get_src_type( nt_packet_t* packet ) {
	return (int) ( packet->node_types >> 4 );
}

int nt_get_dst_type( nt_packet_t* packet ) {
	return (int) ( 0xF & packet->node_types );
}

const char* nt_node_type_to_string( int type ) {
	if( type < NT_NUM_NODE_TYPES ) {
		return nt_node_types[type];
	} else {
		return nt_node_types[NT_NUM_NODE_TYPES];
	}
}

int nt_get_packet_size( nt_packet_t* packet ) {
	if( packet->type < NT_NUM_PACKET_TYPES ) {
		return nt_packet_sizes[packet->type];
	} else {
		return nt_packet_sizes[0];
	}
}

const char* nt_packet_type_to_string( nt_packet_t* packet ) {
	if( packet->type < NT_NUM_PACKET_TYPES ) {
		return nt_packet_types[packet->type];
	} else {
		return nt_packet_types[0];
	}
}

nt_packet_t* nt_packet_copy( nt_packet_t* packet ) {
	if( packet != NULL ) {
		nt_packet_t* to_return = nt_packet_malloc();
		memcpy( to_return, packet, sizeof(nt_packet_t) );
		if( packet->num_deps > 0 ) {
			to_return->deps = nt_dependency_malloc( to_return->num_deps );
			memcpy( to_return->deps, packet->deps, sizeof(nt_dependency_t) * to_return->num_deps );
		}
		return to_return;
	}
	return NULL;
}

void nt_packet_free( nt_packet_t* packet ) {
	if( packet != NULL ) {
		if( packet->num_deps > 0 ) {
			free( packet->deps );
		}
		free( packet );
	}
}

void nt_print_packet( nt_packet_t* packet ) {
	int i;
	// HERE  TODO
	if( packet != NULL ) {
		printf( "  ID:%u CYC:%llu SRC:%u DST:%u ADR:0x%08x TYP:%s NDEP:%u FROM:%s TO:%s DEPS:",
				packet->id, packet->cycle, packet->src,
				packet->dst, packet->addr, nt_packet_type_to_string( packet ),
				packet->num_deps,
				nt_node_type_to_string(nt_get_src_type(packet)),
				nt_node_type_to_string(nt_get_dst_type(packet)));
		for( i = 0; i < packet->num_deps; i++ ) {
			printf( "_%d", packet->deps[i] );
		}
		printf( "\n" );
	} else {
		printf( "WARNING: %s:%d: NULL packet printed!\n", __FILE__, __LINE__ );
	}
}

void nt_free_trheader( nt_header_t* header ) {
	if( header != NULL ) {
		if( header->regions != NULL ) {
			free( header->regions );
		}
		if( header->notes != NULL ) {
			free( header->notes );
		}
		free( header );
	}
}

int nt_get_headersize() {

	#pragma pack(push,1)
	struct nt_header_pack {
		unsigned int nt_magic;
		float version;
		char benchmark_name[NT_BMARK_NAME_LENGTH];
		unsigned char num_nodes;
		unsigned long long int num_cycles;
		unsigned long long int num_packets;
		unsigned int notes_length;  // Includes null-terminating char
		unsigned int num_regions;
		char padding[9];
	};
	#pragma pack(pop)

	if( nt_input_tracefile != NULL ) {
		int to_return = 0;
		to_return += sizeof(struct nt_header_pack);
		to_return += nt_input_trheader->notes_length;
		to_return += nt_input_trheader->num_regions * sizeof(nt_regionhead_t);
		return to_return;
	} else {
		nt_error( "must open trace file with nt_open_trfile before header is available" );
	}
	return -1;
}

void* _nt_checked_malloc( size_t n, char* file, int line ) {
	void* ptr;
	ptr = malloc( n );
	if( ptr == NULL ) {
		fprintf( stderr, "ERROR: bad allocation at %s:%d\n", file, line );
		exit(0);
	}
	return ptr;
}

int nt_little_endian() {
	int to_return = 1;
	union {
		int number;
		char bytes[sizeof(int)];
	} u;
	unsigned int i;
	u.number = (int)0;
	for( i = 0; i < sizeof(int); i++ ) {
		u.number |= (int)(i + 1) << (8 * i);
	}
	for( i = 0; i < sizeof(int); i++ ) {
		if( (unsigned int)u.bytes[i] != i+1 ) {
			to_return = 0;
			break;
		}
	}
	return to_return;
}

void _nt_error( const char* str, char* file, int line ) {
#ifdef DEBUG_ON
	fprintf( stderr, "WARNING: In %s:%d: %s\n", file, line, str );
#else
	fprintf( stderr, "ERROR: In %s:%d: %s\n", file, line, str );
	exit(0);
#endif
}

// Backend functions for creating trace files
void nt_dump_header( nt_header_t* header, FILE* fp ) {

	#pragma pack(push,1)
	struct nt_header_pack {
		unsigned int nt_magic;
		float version;
		char benchmark_name[NT_BMARK_NAME_LENGTH];
		unsigned char num_nodes;
		unsigned char pad;
		unsigned long long int num_cycles;
		unsigned long long int num_packets;
		unsigned int notes_length;  // Includes null-terminating char
		unsigned int num_regions;
		char padding[8];
	};
	#pragma pack(pop)

	if( header != NULL ) {
		struct nt_header_pack* out_header = nt_checked_malloc( sizeof(struct nt_header_pack) );
		out_header->nt_magic = header->nt_magic;
		out_header->version = header->version;
		strcpy( out_header->benchmark_name, header->benchmark_name );
		out_header->num_nodes = header->num_nodes;
		out_header->num_cycles = header->num_cycles;
		out_header->num_packets = header->num_packets;
		out_header->notes_length = header->notes_length;
		out_header->num_regions = header->num_regions;
		fwrite( out_header, sizeof(struct nt_header_pack), 1, fp );
		fwrite( header->notes, sizeof(char), header->notes_length, fp );
		fwrite( header->regions, sizeof(nt_regionhead_t), header->num_regions, fp );
		free( out_header );
	} else {
		nt_error( "dumping NULL header" );
	}
}

void nt_dump_packet( nt_packet_t* packet, FILE* fp ) {

	#pragma pack(push,1)
	struct nt_read_pack {
		unsigned long long int cycle;
		unsigned int id;
		unsigned int addr;
		unsigned char type;
		unsigned char src;
		unsigned char dst;
		unsigned char node_types;
		unsigned char num_deps;
	};
	#pragma pack(pop)

	if( packet != NULL ) {
		fwrite( packet, sizeof(struct nt_read_pack), 1, fp );
		fwrite( packet->deps, sizeof(nt_dependency_t), packet->num_deps, fp );
	} else {
		nt_error( "dumping NULL packet" );
	}
}
