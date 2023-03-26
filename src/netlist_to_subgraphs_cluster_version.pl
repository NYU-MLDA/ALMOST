#! /bin/env perl
########Identify key-gates and features
require 5.004;
use FindBin;    # New in Perl5.004
use List::Util qw/shuffle/;
require "/home/abc586/currentResearch/ML_locking/new_encoding/theCircuit.pm";
use File::Path qw( make_path );
use File::Spec;
my @gate_types=();
my $key_is_given=1;
my @binvalues=();
my $file_name="";
my $assign_count=0;
my $substr="KEYINPUT";
my $ml_count=0;
my @tr=();
my @va=();
my @te=();
my %features_map=();
my %module_map=();
my $top_module="";
$module_map{"key0"}=0;
$module_map{"key1"}=1;
my @modules=();
$features_map{"PI"}=0;
$features_map{"PO"}=1;
$features_map{"KEY"}=2;
$features_map{"XOR"}=3;
$features_map{"XNOR"}=4;
$features_map{"AND"}=5;
$features_map{"OR"}=6;
$features_map{"NAND"}=7;
$features_map{"NOR"}=8;
$features_map{"INV"}=9;
$features_map{"BUF"}=10;
$features_map{"CLKBUF"}=10;
$features_map{"OAI"}=11;
$features_map{"AOI"}=12;
$features_map{"MUX"}=13;
my $start_time               = time;

my ($rel_num)                = '$Revision: 1 $' =~ /\: ([\w\.\-]+) \$$/;
my ($rel_date) = '$Date: 2021/10/13 20:38:38 $' =~ /\: ([\d\/]+) /;
my $prog_name = $FindBin::Script;

my $hc_version = '0.1';

my $help_msg = <<HELP_MSG;
This program resturns a list of all the key-gates subgraphs in a verilog netlist
Usage: $prog_name [options] verilog_file ...

    Options:	-h | -help		Display this info

		-v | -version		Display version & release date


                -i input file name      Input verilog gate level netlist file name

    Example:

    UNIX-SHELL> $prog_name -d out/ -i input_file.v > output_file.txt


HELP_MSG

format INFO_MSG =
     @|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
     $prog_name
     @|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
     "Version $rel_num  Released on $rel_date"
     @|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
     'Lilas Alrahis <lma387@nyu.edu>'
     @|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
     'NYUAD, Abu Dhabi, UAE'

     @|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
     "\'$prog_name -help\' for help"

.

# Allow operator/bareword style usage of these subroutines.
use subs
  qw(PrintWarning PrintError PrintFatalError PrintInternalError PrintDebug);

my $error            = 0;
my $input_file;
my $input_dir;
my $comment = 0;
while ( $_ = $ARGV[0], /^-/ ) {              # Get command line options
    shift;
    if (/^-h(elp)?$/) { $~ = "INFO_MSG"; write; print $help_msg; exit 0 }
    elsif (/^-v(ersion)?$/) { print "$prog_name $rel_num $rel_date\n"; exit 0 }
    elsif (/^-k(ey)?$/)   { $key_size         = shift; }
elsif (/^-f(ile)?$/){$file_name_=shift;}    
elsif (/^-c(omment)?$/)   { $comment          = 1; }
    elsif (/^-i(nput)?$/)     { $input_dir       = shift; }
    elsif (/^-debug$/)        { $debug            = 1 }        # Hidden option
    else                      { PrintError "Unknown option: '$_'!" }
}

if ( !( defined($input_dir) ) ) {
    PrintError "Expect an input Verilog files!";
}



if ( $error > 0 ) {
    warn "\n$help_msg";
    exit 1;
}

select( ( select(STDERR), $~ = "INFO_MSG" )[0] ), write STDERR;

###################################################
#################### Started Here
###################################################

my $status = 0;
my $filename_label = 'label.txt';
my $filename_cell = 'cell.txt';
my $filename_count="count.txt";
#$file_name_="./data/".$file_name_;
system("mkdir -p $file_name_");
open(FH_LINK, '>',"${file_name_}/link.txt") or die $!;
open(FH_NODE_TE_POS, '>',"${file_name_}/node_te_pos.txt") or die $!;
open(FH_NODE_TE_NEG, '>',"${file_name_}/node_te_neg.txt") or die $!;
open(FH_NODE_TR_POS, '>',"${file_name_}/node_tr_pos.txt") or die $!;
open(FH_NODE_TR_NEG, '>',"${file_name_}/node_tr_neg.txt") or die $!;
open(FH_NODE_VA_POS, '>',"${file_name_}/node_va_pos.txt") or die $!;
open(FH_NODE_VA_NEG, '>',"${file_name_}/node_va_neg.txt") or die $!;
open(FH_CELL, '>', "${file_name_}/$filename_cell") or die $!;
open(FH_LABEL, '>', "${file_name_}/$filename_label") or die $!;
open(FH_COUNT, '>', "${file_name_}/$filename_count") or die $!;
my $filename_feat = 'feat.txt';
open(FH_FEAT, '>', "${file_name_}/$filename_feat") or die $!;
opendir my $dh, $input_dir or die "Cannot open $input_dir: $!";
my @input_files = sort grep { ! -d } readdir $dh;
closedir $dh;
foreach my $input_file (@input_files) {
next if ($input_file=~m/^\./);
my $trial=2;
if ($input_file=~m/^Valid/)
{
$trial=1;
} 
elsif ($input_file=~m/^Test/)
{
print "Input file is a Test file $input_file\n";
$trial=2;
}
elsif($input_file=~m/^Train/)
{
$trial=3;
}
my %the_circuit              = ();
my @module_ids=();
my $module_id="";  
my @list_of_gates=();
my %Netlist_Outputs_Hash =();
my %Netlist_Inputs_Hash=();
    my $cell_name           = "";
    my $instance_name       = ""; 
    my @ports               = ();
    my %ports               = ();
    my $multi_line_statment = "";
    my $connect_this_line   = 0;
    my $a                   = "";
    my $line                = "";
    my @Netlist_Inputs      = ();
    my @Netlist_Outputs     = ();


    local *INPUT_FH;     # Only way to declare a non-global filehandler.

    ##################Now I wanna parse again to get the list of inputs, outputs and gates
    open INPUT_FH, "${input_dir}/${input_file}"
      or PrintFatalError "Can't open input file '$input_file': $!!";
   
#print "input file is $input_file\n";
 while (<INPUT_FH>) {
        $line = $_;
   
    if ($line=~m/\/\/Secret key is\'/) ###TODO, this is be based on how you dump the key
{
my $key=$line;
$key=~s/\/\/Secret key is\'//g;

$key=~s/\.\.//g;
$key=~s/\/\/\'//g;
chomp($key);
print "$key\n";
 @binvalues = split(" ", $key);
$key_is_given=1;

print "@binvalues\n";}






	if ( $line =~ /^\s*(module)\s+(\w+)\b/ ) {
             $module_id             = $2;
			 $top_module=$module_id;

             
				}
			 elsif ($line =~ /^\s*(endmodule)\b/) {
			 
			 }
        elsif ( $line =~ /^\s*(input)\s+.*/ ) {    #############check inputs

            #if defined on one line then
            if ( $line =~ /^.*?\;\s*$/ ) {
                $line =~ s/input\s+//;             #remove the input word
                $line =~ tr/;//d;               #remove semicolomn
                                                #trim $line;
                for ($line) {
                    s/^\s+//;

                }
                $line =~ s/\R//g;
                my @found_inputs = split( /,/, $line ); #it was \s+
push @Netlist_Inputs, @found_inputs;
#foreach my $inn (@found_inputs){
#$inn=~ s/^\s+|\s+$//g;
#push @Netlist_Inputs, $inn;}
                next;    # port is defined on single line so exit
            }
            else {       #port is defined on more than one line
                until ( $line =~ /^.*?\;\s*$/ ) {

                    #read more. But What happened to the one I read before?

                  $line =~ s/input\s+//g;     #remove the input word
                    $line =~ tr/;//d;       #remove semicolomn

                    for ($line) {
                        s/^\s+//;

                    }
                    #$line =~ tr/,//d;       #remove coma
                    $line =~
                      s/\R//g;   #remove new lines and replace with white spcaes
                    my @found_inputs = split( /,/, $line );
		    
push @Netlist_Inputs, @found_inputs;
		    #foreach my $inn (@found_inputs){
	#$inn=~ s/^\s+|\s+$//g;
#push @Netlist_Inputs, $inn;}
                    $line = <INPUT_FH>;

                }                       #End of multiline detection
                $line =~ s/input\s+//g;     #remove the input word
                $line =~ tr/;//d;       #remove semicolomn

                for ($line) {
                    s/^\s+//;
                }
              #  $line =~ tr/,//d;       #remove coma
                $line =~
                  s/\R//g;    #remove new lines and replace with white spcaes
                my @found_inputs = split( /,/, $line );

push @Netlist_Inputs, @found_inputs;
		#foreach my $inn (@found_inputs){
	#$inn=~ s/^\s+|\s+$//g;
#push @Netlist_Inputs, $inn;}
                next;
            }
        }    #### end of input detection

        if ( $line =~ /^\s*(output)\s+.*/ ) {    #############check outputs

            #if defined on one line then
            if ( $line =~ /^.*?\;\s*$/ ) {
                $line =~ s/output//;             #remove the output word
                $line =~ tr/;//d;                #remove semicolomn

                for ($line) {
                    s/^\s+//;
                }
                #$line =~ tr/,//d;                #remove coma
                $line =~ s/\R//g;                #remove new lines
                my @found_outputs = split( /,/, $line );   ### take one by one
              
foreach my $inn (@found_outputs){
$inn=~ s/^\s+|\s+$//g;
push @Netlist_Outputs, $inn;}
	      	next;    # port is defined on single line so exit
            }
            else {       #port is defined on more than one line
                until ( $line =~ /^.*?\;\s*$/ ) {

                    #read more. But What happened to the one I read before?

                    $line =~ s/output//g;    #remove the input word
                    $line =~ tr/;//d;        #remove semicolomn

                    for ($line) {
                        s/^\s+//;

                    }
                    $line =~
                      s/\R//g;   #remove new lines and replace with white spcaes
                    my @found_outputs = split( /,/, $line );
                    
foreach my $inn (@found_outputs){
$inn=~ s/^\s+|\s+$//g;
push @Netlist_Outputs, $inn;}
		    
		    $line = <INPUT_FH>;

                }                        #End of multiline detection
                $line =~ s/output//g;    #remove the output word
                $line =~ tr/;//d;        #remove semicolomn

                for ($line) {
                    s/^\s+//;
                }
                $line =~
                  s/\R//g;    #remove new lines and replace with white spcaes
                my @found_outputs = split( /,/, $line );

foreach my $inn (@found_outputs){
$inn=~ s/^\s+|\s+$//g;
push @Netlist_Outputs, $inn;}
                next;
            }
        } 

        
    }
    close INPUT_FH;

my @tempp=();
foreach my $inn (@Netlist_Inputs){
$inn=~ s/^\s+|\s+$//g;
if ($inn=~m/\s*\[(\d+)\:(\d+)\]\s+(\S+)/){
my $start=$1;
my $end=$2;
my $name=$3;
#print "for $inn it is $name and $end\n";
my $i=$start;
if ($start>$end){
$i=$end;
$end=$start;
print "start is now $i and end is now $end\n";
}
while ($i<=$end)
{
push @tempp, "$name\[$i\]";
$i++;
}

}
else{
push @tempp, $inn;
}
}
 @Netlist_Inputs=@tempp;
   @tempp=();


 #print "The outputs of the netlist are @Netlist_Outputs\n"  ;    ###############Initializing the circuit with the outputs
 print "The inputs of the netlist are @Netlist_Inputs\n" ;    ###############Initializing the circuit with the inputs
  

 
    %Netlist_Outputs_Hash = map { $_ => 1 } @Netlist_Outputs;
     %Netlist_Inputs_Hash  = map { $_ => 1 } @Netlist_Inputs;
     #print "This is my hash\n";# %Netlist_Inputs_Hash\n";    
     #print Dumper(\%Netlist_Inputs_Hash);
#######################open file again to initialize the circuit
    
	open INPUT_FH, "${input_dir}/${input_file}"
      or PrintFatalError "Can't open input file '$input_file': $!!";
    while (<INPUT_FH>) {
        @ports = ();
        %ports = ();
        $line  = $_;
  #   print "I am reading a line $line\n";
	if ( $line =~ /^\s*(wire)\s+.*/ ) {    #############check inputs
#print "Yes it is a line\n";
        }    #### end of wire detection

if ($line=~m/^\s*assign\s+(\S*)\s+=\s+(\S*)\;/){
my $out=$1;
my $in=$2;

my $modified_name="assign_${assign_count}";

push @list_of_gates, $modified_name;
#print "Assign statement with $out and $in\n ";
my $current_object;
my @current_gate_inputs=();
push @current_gate_inputs, $in;
my @current_gate_outputs=();
push @current_gate_outputs, $out;
					if ($trial==3 ){
						  push @tr, $ml_count;
						 # print FH_TR "$ml_count\n";
						  }
						  elsif ($trial==1){
						  push @va, $ml_count;
						 # print FH_VA "$ml_count\n";
						  }
						  else {
						  push @te, $ml_count;
						 
print "I am in testing and I have ml count $ml_count\n";
# print FH_TE "$ml_count\n";  
						  }	
                    $current_object = theCircuit->new(
                        {	
                            name          => $modified_name, #$instance_name,
                            bool_func     => "BUF",
                            inputs        => \@current_gate_inputs,
                            outputs        => \@current_gate_outputs,
                            fwdgates => [undef],
			    processed => $module_id,
                            fwdgates_inst => [undef],
                            count =>$ml_count,
                        }
                    );
			my $indicator=0;
	 	foreach my $current_gate_output (@current_gate_outputs){
                    if ( exists( $Netlist_Outputs_Hash{$current_gate_output} ) )
                    { 
					my @temp=();
					my @temp_inst=();
					if ($indicator==0){
					
                    push @temp, "PO";
                    
                    push @temp_inst, $current_gate_output;
					}
					else{
					@temp=$current_object->get_fwdgates();
					@temp_inst=$current_object->get_fwdgates_inst();
					push @temp, "PO";
                    
                    push @temp_inst, $current_gate_output;
					}
					$indicator++;
					
					
                      $current_object->set_fwdgates(\@temp);
                      $current_object->set_fwdgates_inst(\@temp_inst);
                    }
					}
                                    $the_circuit{$modified_name} = $current_object;
$ml_count++;
$assign_count++;
}
elsif ($line  =~ m/

	^\s*
	(\S*)  # Cell name
	\s+
	(\S*?)\s*?\( 
	.+   #ports list
	$/x
       ){
	
      if ( $line =~ /\;/ )
	{
	  
	} else {
	  until ( $line =~ /\;\s*$/ )
	    {
	  
$line =~ s/^\s+|\s+$//g;
    chomp($line);
	      $multi_line_statment .= $line;
	      $line = <INPUT_FH>;
	    }

	  $line =~ s/^\s+//g;
	  $line = $multi_line_statment.$line;
	  $multi_line_statment = "";
	  
	}

    }
    if ( $line =~ /^\s*(module)\s+(\w+)\b/ ) {
             $module_id             = $2;
			 
			 
             }
		
	elsif ($line =~ /^\s*(endmodule)\b/) {
			 @Module_Wires=();
			 %wire_params=();
			 }
    if (!($line =~m/module/)){
    if ($line =~ m/
	^\s*
	(\S*)  # Cell name
	\s+
	
	(\S*?)\s*?\( 
	(.+)   #ports list
	\)
	\s*
	\;
	\s*
	$
	/x
       ) {
      $cell_name = $1;
      $instance_name = $2;

      @ports = split/,/, $3;

                foreach $a (@ports) {
                    $a =~ /\s*\.([A-Za-z0-9]*?)\(\s*(\S*)\s*\)/;
                    $ports{$1} = $2;
                }
                my $hash_ref = \%ports;
               my $current_object;
my @current_gate_inputs=();
if ( defined( $$hash_ref{"A"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"A"};

                    }

  if ( defined( $$hash_ref{"D"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"D"};

                    }
                                     if ( defined( $$hash_ref{"B"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"B"};

                    }
  if ( defined( $$hash_ref{"A1N"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"A1N"};

                    }

  if ( defined( $$hash_ref{"B0N"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"B0N"};

                    }
                                     if ( defined( $$hash_ref{"B1N"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"B1N"};

                    }
  if ( defined( $$hash_ref{"A0N"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"A0N"};

                    }

  if ( defined( $$hash_ref{"E"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"E"};

                    }
                                     if ( defined( $$hash_ref{"F"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"F"};

                    }


  if ( defined( $$hash_ref{"S0"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"S0"};

                    }

  if ( defined( $$hash_ref{"S1"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"S1"};

                    }
                            
 if ( defined( $$hash_ref{"BN"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"BN"};

                    }
 if ( defined( $$hash_ref{"AN"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"AN"};

                    }
 if ( defined( $$hash_ref{"DN"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"DN"};

                    }
 if ( defined( $$hash_ref{"C"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"C"};

                    }
 if ( defined( $$hash_ref{"C1"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"C1"};

                    }
                    
                    if ( defined( $$hash_ref{"C2"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"C2"};

                    }
 if ( defined( $$hash_ref{"CI"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"CI"};

                    }
                    
                    if ( defined( $$hash_ref{"B2"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"B2"};

                    }
 if ( defined( $$hash_ref{"B1"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"B1"};

                    }
                    
 if ( defined( $$hash_ref{"B0"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"B0"};

                    }

 if ( defined( $$hash_ref{"B0N"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"B0N"};

                    }

 if ( defined( $$hash_ref{"C0"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"C0"};

                    }
                    if ( defined( $$hash_ref{"A"} ) &&  defined( $$hash_ref{"B"} )&& defined( $$hash_ref{"S"} ) && defined( $$hash_ref{"Z"} )){
                        push @current_gate_inputs, $$hash_ref{"S"};

                    }

 if ( defined( $$hash_ref{"A3"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"A3"};

                    }
                    
 if ( defined( $$hash_ref{"A0"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"A0"};

                    }
                    if ( defined( $$hash_ref{"A4"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"A4"};

                    }

 if ( defined( $$hash_ref{"A1"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"A1"};

                    }
                    
                    if ( defined( $$hash_ref{"A2"} ) ) {
                        push @current_gate_inputs, $$hash_ref{"A2"};

                    }
my @current_gate_outputs=();
   
#print "the inputs are @current_gate_inputs\n";
                 
                    
if (   defined($$hash_ref{"D"}) && defined($$hash_ref{"Q"})  ){

push @current_gate_outputs , $$hash_ref{"Q"};

}

elsif (   defined($$hash_ref{"CO"}) && defined($$hash_ref{"S"})  ){


push @current_gate_outputs,$$hash_ref{"S"};
push @current_gate_outputs, $$hash_ref{"CO"};
}
elsif(defined($$hash_ref{"CO"})){

push @current_gate_outputs , $$hash_ref{"CO"};


}
elsif (defined($$hash_ref{"D"}) && !(defined($$hash_ref{"Q"})) && !(defined($$hash_ref{"Y"}))){
if (defined($$hash_ref{"QN"})){
push @current_gate_outputs , $$hash_ref{"QN"};
}
}
		    elsif (defined $$hash_ref{"Y"}){
 push @current_gate_outputs , $$hash_ref{"Y"};

                   }



                    elsif (defined $$hash_ref{"ZN"}){
                    push @current_gate_outputs , $$hash_ref{"ZN"};
                    }
                    elsif (defined $$hash_ref{"Z"}){
                    push @current_gate_outputs , $$hash_ref{"Z"};
                    }
					#print "cell name is $cell_name\n";
					my $bool_fun=$cell_name;
					$bool_fun=~s/\_\S+//g;
					$bool_fun=~s/\d+\D*$//g;
					push @gate_types, $bool_fun;
					#print "bool is $bool_fun\n";
					my @updates=();

					my $modified_name="${instance_name}";
						  push @list_of_gates, $modified_name;
						 if ($trial==3 ){
						  push @tr, $ml_count;
						  }
						  elsif ($trial==1){
						  push @va, $ml_count;
						  }
						  else {
						  push @te, $ml_count;
print "I am in testing and I have ml count $ml_count\n";
						  }
$module_id=$top_module;
                    $current_object = theCircuit->new(
                        {	
                            name          => $modified_name, #$instance_name,
                            bool_func     => $bool_fun,
                            inputs        => \@current_gate_inputs,
                            outputs        => \@current_gate_outputs,
                            fwdgates => [undef],
							processed => $module_id,
                            fwdgates_inst => [undef],
                            count =>$ml_count,
                        }
                    );
#print "This is the instance name $instance_name and those are the outputs @current_gate_outputs\n";
					my $indicator=0;
					foreach my $current_gate_output (@current_gate_outputs){
                    if ( exists( $Netlist_Outputs_Hash{$current_gate_output} ) )
                    { 
					my @temp=();
					my @temp_inst=();
					if ($indicator==0){
					
                    push @temp, "PO";
                    
                    push @temp_inst, $current_gate_output;
					}
					else{
					@temp=$current_object->get_fwdgates();
					@temp_inst=$current_object->get_fwdgates_inst();
					push @temp, "PO";
                    
                    push @temp_inst, $current_gate_output;
					}
					$indicator++;
					
					
                      $current_object->set_fwdgates(\@temp);
                      $current_object->set_fwdgates_inst(\@temp_inst);
                    }
					}
                                    $the_circuit{$modified_name} = $current_object;
                $ml_count++;
               
                    
             }       
                

}
      }


        #######end of opening file again
    close INPUT_FH;
    ############################

 
foreach my $object ( values %the_circuit ) {  ##### loop through the gates
my $name="";
$name= $object->get_name();

#print "the name is $name\n";
my @current_inputss=$object->get_inputs();
#print "the inputs are @current_inputss\n"; 


my $limit=0;
$limit=@current_inputss;
my @current_inputs=();
my @current_gate_inputs=();
my @current_gate_inputs_inst=();
#print "original limit is $limit\n";
my $outer_gate_type=$object->get_bool_func();

for my $i_index (0 .. $#current_inputss)
{
my $in=   $current_inputss[$i_index];
print "O am processing this inpit $in\n";
if ( exists( $Netlist_Inputs_Hash{$in} ) )
 {	
print "It has been identified as a PI\n";
  if (index($in, $substr) != -1)
 {
 print "Did I enter?\n";
 push @current_gate_inputs_inst,$in;
my $key_id=0; 

push @current_gate_inputs, "KI";
if ($in=~m/KEYINPUT(\d+)/)
 { $key_id=$1;
	print "This is the keyinput ID $key_id\n";
 }
 
 if ($key_id<=63){
print "$in is a keyinput less than 64\n";
if ($trial==2){
print "But it is testing\n";

if ($key_is_given==1){
	 if ($binvalues[$key_id] eq "0") {
		 $object->set_processed('key0');
	 }
	 else {$object->set_processed('key1');}
 }
 else
 {

if ($key_id%2==0){
		 $object->set_processed('key1');
	 }
	 else {$object->set_processed('key0');}

 }
}
else {
print "and it is not testing"

}

}
else {
print "$in is a keyinput larger or equal to 64.";


if ($key_is_given==1){
	 if ($binvalues[$key_id] eq "0") {
		 $object->set_processed('key0');
	 }
	 else {$object->set_processed('key1');}
 }
 else
 {

if ($key_id%2==0){
		 $object->set_processed('key1');
	 }
	 else {$object->set_processed('key0');}

 }
}

 $limit--;
 }
 else{
 push @current_gate_inputs, "PI";
 push @current_gate_inputs_inst,$in;
 $limit--;
	 
 }
	
	
}#end if it is a PI
else{
	
push @current_inputs, $in;	
}#end if it is not a PI
}# end of looping through the inputs


 if ($limit!=0){ #if my input array is not empty
OUTER: 
##I wanna loop through all the gates, and check if any gate's output is actually one of the inputs
foreach my $instance (@list_of_gates)
  {
#print " my input $instance\n";
		   my $current_objectt ="";
		   my @current_outputs=();
	
                   $current_objectt = $the_circuit{$instance};
	  @current_outputs= $current_objectt->get_outputs();
		   my $current_gate_type="";
		   
               
                   
                   $current_gate_type=$current_objectt->get_bool_func();
                #print "my utputs are @current_outputs\n";

		   foreach my $current_output (@current_outputs){
		                      foreach my $input (@current_inputs)
                   {

                   if ($input eq $current_output)
                   { #print "found a match from isnatnce $instance with output $current_output that matches my input $input\n";
                   push @current_gate_inputs, $current_gate_type;
                   push @current_gate_inputs_inst, $instance;
                   # need to fix here to check if i added before
                   my @temp=();
                   my @temp_inst=();
                    if ($current_objectt->get_fwdgates()){
                   @temp=$current_objectt->get_fwdgates();
                   @temp_inst=$current_objectt->get_fwdgates_inst();
                   }
                   push @temp, $outer_gate_type;
                   push @temp_inst, $name;
                   @temp = grep defined, @temp;
                   @temp_inst = grep defined, @temp_inst;
                    $current_objectt->set_fwdgates(\@temp);
                    $current_objectt->set_fwdgates_inst(\@temp_inst);
     
                       $the_circuit{ $instance } = $current_objectt;
                   }#the input is a primary output of a gate
                   
                   }
}
}
}#end if my input array is not empty
$object->set_fedbygates(\@current_gate_inputs);

$object->set_fedbygates_inst(\@current_gate_inputs_inst);
  $the_circuit{ $name } = $object;
  
}#end of the outer loop through the gates
my %params_tr = map { $_ => 1 } @tr;

my %params_te = map { $_ => 1 } @te;
my %params_va = map { $_ => 1 } @va;

	#######end of initalizinf the circuit and fwd instances

@gate_types=uniq(@gate_types);

print "Found these gates @gate_types\n";
	foreach my $object ( values %the_circuit ) {  ##### loop through the gates

my @OUts=$object->get_fwdgates();
my @features_array=(0) x 14; #IT USED TO BE 11
my $label="";
my $module_name=$object->get_processed();
if(exists($module_map{$module_name})){
$label=$module_map{$module_name};
}
elsif ($module_name=~m/key0/){

$label=0;
}
elsif ($module_name=~m/key1/){
$label=1;
}
else {
	$label=2; #it is an adder circuit eitheer look ahead, carry skip and so on
}
my $prev=$features_array[$features_map{$object->get_bool_func()}];
$features_array[$features_map{$object->get_bool_func()}]=($prev+1);
my @INputs=$object->get_fedbygates();

my %params = map { $_ => 1 } @INputs;
if(exists($params{"PI"})) { 
my $prev=0;
$features_array[$features_map{"PI"}]=($prev+1);


 }
if(exists($params{"KI"})) {
	my $prev=0;
$features_array[$features_map{"KEY"}]=($prev+1); 
#print "This gate is connected to KI $nameo\n";
#print "@features_array\n";
}

my $name="";
$name= $object->get_name();
my $count=$object->get_count();

if(exists($params_tr{$count})) { 
#here
if ($label==0){
####
print FH_NODE_TR_POS "$count\n";

}
elsif($label==1){

print FH_NODE_TR_NEG "$count\n";

}
}
elsif(exists($params_te{$count})) { 
if ($label==0){
print FH_NODE_TE_POS "$count\n";

}

elsif($label==1){

print FH_NODE_TE_NEG "$count\n";

}
else {
	#print "What is my label? $label"
	}
}

elsif(exists($params_va{$count})) { 
#here
if ($label==0){
print FH_NODE_VA_POS "$count\n";

}

elsif($label==1){

print FH_NODE_VA_NEG "$count\n";

}
}
my @current_fwd_gates=();
@current_fwd_gates=$object->get_fwdgates_inst();
foreach my $elem (@current_fwd_gates){
if (exists ($the_circuit{$elem}))  {
my $current_ob=$the_circuit{$elem};
my $current_count=$current_ob->get_count();
my $inputt=$current_ob->get_bool_func();
my @INNputs=$current_ob->get_fwdgates();
print FH_LINK "$count $current_count\n";
#print FH_LINK "$current_count $count\n";
#print FH_ROW "$count\n";
#print FH_COL "$current_count\n";
#print FH_COL "$count\n"; #SO THAT THERE IS NO DIRECTION
#print FH_ROW "$current_count\n";
#if(exists($params_tr{$current_count})) {
#print FH_ROW_TR "$count\n";
#print FH_COL_TR "$current_count\n";
#print FH_ROW_TR "$current_count\n";
#print FH_COL_TR "$count\n";
}
#}
}

%params=();
#print "These are outs @OUts\n";
%params = map { $_ => 1 } @OUts;
my $check_flag=0;
if(exists($params{"PO"})) { #$features_array[$features_map{"PO"}]=1;
#my $indexxx=$features_map{"PO"};
#print "This is the PO index $indexxx\n";
#print "This gate is connected to PO $nameo\n";
my $prev=0;
$features_array[$features_map{"PO"}]=($prev+1);
#print "@features_array\n";

print FH_LINK "$count $count\n";
#my $current_count=$object->get_count();
#print FH_ROW "$count\n";
#print FH_COL "$count\n";
#if(exists($params_tr{$count})) { 
#print FH_ROW_TR "$count\n";
#print FH_COL_TR "$count\n";
#}#if the node is training node

}

print FH_CELL "$count $name from file $input_file\n";
print FH_COUNT "$count\n";

#print FH_LABEL "@labels_array\n";
print FH_LABEL "$label\n";
my $size=@features_array;
print FH_FEAT "@features_array\n";
}#end of the outer loop through the gates
#newly added loop
}
close(FH_ROW);
close(FH_FEAT);
close(FH_CELL);
close(FH_COUNT);
close(FH_LABEL);
close(FH_COL);
close(FH_COL_TR);
close(FH_ROW_TR);
close(FH_VA);
close(FH_TE);
close(FH_TR);
my $run_time = time - $start_time;
print STDERR "\nProgram completed in $run_time sec ";

if ($error) {
    print STDERR "with total $error errors.\n\n" and $status = 1;
}
else {
    print STDERR "without error.\n\n";
}

exit $status;

sub PrintWarning {
    warn "WARNING: @_\a\n";
}

sub PrintError {
    ++$error;
    warn "ERROR: @_\a\n";
}

sub PrintFatalError {
    ++$error;
    die "FATAL ERROR: @_\a\n";
}

sub PrintInternalError {
    ++$error;
    die "INTERNAL ERROR: ", (caller)[2], ": @_\a\n";
}
sub uniq {
    my %seen;
    grep !$seen{$_}++, @_;
}
sub PrintDebug {
    my $orig_list_separator = $";
    $" =
      ',';   # To print with separator, @some_list must be outside double-quotes
    warn "DEBUG: ", (caller)[2], ": @_\n" if ($debug);
    $" = $orig_list_separator;    # Dummy " for perl-mode in Emacs
}



__END__

