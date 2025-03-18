#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdbool.h>
#include "queue.h"
#include "netrace.h"

int main( int argc, char** argv ) {
	// Read command line arguments
	char* tracefile;
	int region = -1;
	long long int packet_limit = 1000000000;
	int packets_in_region;
	long long int start_cycle = 0;
	long long int start_id = -1;
	// Trace file
	nt_context_t* ctx;
	nt_header_t* header;
	if( argc > 1 ) {
		tracefile = argv[1];
	} else {
		printf( "ERROR: Please specify trace file (first argument)\n" );
		exit(0);
	}
	// Region
	if( argc > 2 ) {
		region = atoi(argv[2]);
	}
	// Packet limit
	if( argc > 3 ) {
		packet_limit = atoi(argv[3]);
	}
	// Open the trace file using netrace
	ctx = calloc( 1, sizeof(nt_context_t) );
	nt_open_trfile( ctx, tracefile );
	// Get trace header
	header = nt_get_trheader( ctx );
	// Skip to the specified region
	if (region >= 0) {
		packets_in_region = header->regions[region].num_packets;
		nt_seek_region( ctx, &header->regions[region] );
		// Compute the cycle in which the region starts
		for(int i = 0; i < region; i++ ) {
			start_cycle += header->regions[i].num_cycles;
		}
	}
	else {
		packets_in_region = header->num_packets;
	}
	// Variables to store packet information
	nt_packet_t* packet;
	unsigned int id;
	unsigned int dep_packet_id;
	unsigned long long int cycle;
	unsigned char type_num;
	unsigned char src_id;
	unsigned char dst_id;
	unsigned char num_deps;
	int src_type_num;
	int dst_type_num;
	const char* src_type_str;
	const char* dst_type_str;
	// Read all packets
	printf( "{\n" );
	printf( "\"nodes\" : %i,\n", header->num_nodes );
	printf( "\"packets\" : \n");
	printf( "[\n" );
	for(int i = 0; (i < packets_in_region) && (i < packet_limit); i++ ) {
		packet = nt_read_packet( ctx );
		// Set the start-id to remap all ids
		if(i == 0){
			start_id = packet->id;
		}
		// Extract information relevant for us
		id = packet->id - start_id;
		cycle = packet->cycle - start_cycle;
		type_num = packet->type;
		src_id = packet->src;
		dst_id = packet->dst;
		src_type_num = nt_get_src_type(packet);
		dst_type_num = nt_get_dst_type(packet);
		src_type_str = nt_node_type_to_string(src_type_num);
		dst_type_str = nt_node_type_to_string(dst_type_num);
		char* line = "{\"id\" : %u, \"cycle\" : %llu, \"type\" : %hhu, \"src\" : %hhu, \"dst\" : %hhu, \"src_type\" : \"%s\", \"dst_type\" : \"%s\", \"reverse_dependencies\" : [";
		printf(line, id, cycle, type_num, src_id, dst_id, src_type_str, dst_type_str);
		bool first = true;
		for (int j = 0; j < packet->num_deps; j++) {
			dep_packet_id = packet->deps[j] - start_id;
			if ((dep_packet_id < packet_limit) && (dep_packet_id < packets_in_region)){
				if (!first) {
					printf(",");
				}
				printf("%u", dep_packet_id);
				first = false;
			}
		}
		printf("]}");
		if ((i < packets_in_region - 1) && (i < packet_limit - 1)) {
			printf(",");
		}
		printf("\n");
	}
	printf( "]\n" );
	printf( "}" );
	nt_close_trfile( ctx );
}

