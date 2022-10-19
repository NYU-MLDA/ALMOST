#! /bin/env perl
require 5.004;
use FindBin;    # New in Perl5.004
use File::Basename;
use File::Path qw(make_path);
use Data::Dumper;
use List::Util qw/shuffle/;


my @secret_key=();
my @x = (0,1);
my $my_lib="";
my %hash=();
my $key;
my @a=(1);
my $type=1;
my $vary=0;
my $value;
my $body="";

my $RLL_key_status =$x[rand @x];
#my $RLL_key_status =1;
my $RLL_track_key=64; #we start from 64
my %RLL_key_map=();
my $header="";
my $key_size=0;
my $wires="";
my $module_declaration="";
my $code="";
my @list_of_gates_original=();
my $ml_count=0;
my %the_circuit              = ();
my $module_id="";  
my @list_of_gates=();
my $start_time               = time;
my %Netlist_Outputs_Hash =();
my %Netlist_Inputs_Hash=();
my ($rel_num)                = '$Revision: 1.7 $' =~ /\: ([\w\.\-]+) \$$/;
my ($rel_date) = '$Date: 2019/10/07 20:38:38 $' =~ /\: ([\d\/]+) /;
my $prog_name = $FindBin::Script;

my $hc_version = '0.1';

my $help_msg = <<HELP_MSG;
This program resturns a list of all the subgraphs in a verilog netlist
Usage: $prog_name [options] verilog_file ...

    Options:	-h | -help		Display this info

		-v | -version		Display version & release date


                -i input file name      Input verilog gate level netlist file name
                -k | -key   locking key size

    Example:

    UNIX-SHELL> $prog_name -k 32 -i input_file.v -o ./RLL_locked_ISCAS/MUX/locked_circuit.v


HELP_MSG

format INFO_MSG =
     @|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
     $prog_name
     @|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
     "Version $rel_num  Released on $rel_date"
     @|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
     'Lilas Al Rahis <lilas.alrahis@kustar.ac.ae>'
     @|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
     'Khalifa Univerity, Abu Dhabi, UAE'

     @|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
     "\'$prog_name -help\' for help"

.

# Allow operator/bareword style usage of these subroutines.
use subs
  qw(PrintWarning PrintError PrintFatalError PrintInternalError PrintDebug);
my ( $output_dir, $debug ) = ( './', 0 );    # Default values for options
my $error            = 0;
my $input_file;
my $output_file;
my $comment = 0;
while ( $_ = $ARGV[0], /^-/ ) {              # Get command line options
    shift;
    if (/^-h(elp)?$/) { $~ = "INFO_MSG"; write; print $help_msg; exit 0 }
    elsif (/^-v(ersion)?$/) { print "$prog_name $rel_num $rel_date\n"; exit 0 }
    elsif (/^-k(ey)?$/) {$key_size=shift;}
    elsif (/^-c(omment)?$/)   { $comment          = 1; }
    elsif (/^-i(nput)?$/)     { $input_file       = shift; }

    elsif (/^-l(ib)?$/)     { $my_lib       = shift; }
    elsif (/^-o(utput)?$/)     { $output_dir       = shift; }
      elsif(/^-a/) {$a_in=shift;
               
                 @a = split( /,/, $a_in );
                 $type = $a[ rand @a ];
                 
                 }
        elsif (/^-f(ile)?$/)     { $output_file       = shift; }
      elsif (/^-va(ry)?$/)     { $vary=1;}
    elsif (/^-debug$/)        { $debug            = 1 }        # Hidden option
    else                      { PrintError "Unknown option: '$_'!" }
}

if ( !( defined($input_file) ) ) {
    PrintError "Expect an input Verilog files!";
}



map { PrintError "Can't open input file '$_'!" unless -f $_ && -T _ }
  $input_file;



if ( $error > 0 ) {
    warn "\n$help_msg";
    exit 1;
}

select( ( select(STDERR), $~ = "INFO_MSG" )[0] ), write STDERR;

###################################################
#################### Started Here
###################################################

my $status = 0;


foreach my $input_file ($input_file) {
    my $directives          = "";
    my $module_started      = 0;
    my $modules_count       = 0;
    
    my $cell_name           = "";
   
    my $instance_name       = "";
  
    my @ports               = ();
    my %ports               = ();
    my $multi_line_statment = "";
    my $connect_this_line   = 0;
    my $a                   = "";
    my $line                = "";
    my $in_file             = basename $input_file;
    my @Netlist_Inputs      = ();
    my @Netlist_Outputs     = ();



    local *INPUT_FH;     # Only way to declare a non-global filehandler.

    ##################Now I wanna parse again to get the list of inputs, outputs and gates
    open INPUT_FH, $input_file
      or PrintFatalError "Can't open input file '$input_file': $!!";
    while (<INPUT_FH>) {
        $line = $_;
                
    if ($line=~m/\/\/Secret key is\'/) ###TODO, this is be based on how you dump the key
{
my $key=$line;
$key=~s/\/\/Secret key is\'//g;

$key=~s/\.\.//g;
$key=~s/\'//g;
chomp($key);
#print "$key\n";
my @binvalues = split(" ", $key);
push @secret_key, @binvalues;}

#print"KEY is given!\n";
#print "@binvalues\n";}




if ( $line =~ /^\s*(module)\s+(\w+)\b/ ) {
             $module_id             = $2;
             }
        if ( $line =~ /^\s*(input)\s+.*/ ) {    #############check inputs

            #if defined on one line then
            if ( $line =~ /^.*?\;\s*$/ ) {
                $line =~ s/input//;             #remove the input word
                $line =~ tr/;//d;               #remove semicolomn
                                                #trim $line;
                for ($line) {
                    s/^\s+//;

                    #s/\s+$//;
                }
                $line =~ tr/,//d;               #remove coma
                $line =~ s/\R//g;
                my @found_inputs = split( /\s+/, $line );
                push @Netlist_Inputs, @found_inputs;
                next;    # port is defined on single line so exit
            }
            else {       #port is defined on more than one line
                until ( $line =~ /^.*?\;\s*$/ ) {

                    #read more. But What happened to the one I read before?

                    $line =~ s/input//g;    #remove the input word
                    $line =~ tr/;//d;       #remove semicolomn

                    for ($line) {
                        s/^\s+//;

                    }
                    $line =~ tr/,//d;       #remove coma
                    $line =~
                      s/\R//g;   #remove new lines and replace with white spcaes
                    my @found_inputs = split( /\s+/, $line );
                    push @Netlist_Inputs, @found_inputs;
                    $line = <INPUT_FH>;

                }                       #End of multiline detection
                $line =~ s/input//g;    #remove the input word
                $line =~ tr/;//d;       #remove semicolomn

                for ($line) {
                    s/^\s+//;
                }
                $line =~ tr/,//d;       #remove coma
                $line =~
                  s/\R//g;    #remove new lines and replace with white spcaes
                my @found_inputs = split( /\s+/, $line );
                push @Netlist_Inputs, @found_inputs;

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
                $line =~ tr/,//d;                #remove coma
                $line =~ s/\R//g;                #remove new lines
                my @found_outputs = split( /\s+/, $line );   ### take one by one
                push @Netlist_Outputs,   @found_outputs;
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
                    $line =~ tr/,//d;        #remove coma
                    $line =~
                      s/\R//g;   #remove new lines and replace with white spcaes
                    my @found_outputs = split( /\s+/, $line );
                    push @Netlist_Outputs,   @found_outputs;
                    $line = <INPUT_FH>;

                }                        #End of multiline detection
                $line =~ s/output//g;    #remove the output word
                $line =~ tr/;//d;        #remove semicolomn

                for ($line) {
                    s/^\s+//;
                }
                $line =~ tr/,//d;        #remove coma
                $line =~
                  s/\R//g;    #remove new lines and replace with white spcaes
                my @found_outputs = split( /\s+/, $line );
                push @Netlist_Outputs,   @found_outputs;

                next;
            }
        } 
        ###HERE I NEED TO DETECT THE GATES
         
                 
if ($line  =~ m/
	^\s*
	(\S*)  # Cell name
	\s+
	
	(\S*?)\s*?\(  #Instance Name
	.+   #ports list
	$/x
       ){
	
      if ( $line =~ /^.*?\;\s*$/ )
	{
	  
	} else {
	  until ( $line =~ /^.*?\;\s*$/ )

	    {
$line =~ s/^\s+|\s+$//g;
	      chomp($line);
	      $multi_line_statment .= $line;
	      $line = <INPUT_FH>;
	    }

$line =~ s/^\s+|\s+$//g;
#	chomp($line);
	  $line = $multi_line_statment.$line;
	  $multi_line_statment = "";
	  ;
	}

    }

    
    if ($line =~ m/
	^\s*
	(\S*)  # Cell name
	\s+
	
	(\S*?)\s*?\(  #Instance Name
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
if (!($line=~m/RLL_wire/)){
if (!($instance_name=~m/RLL_XOR/) && !($instance_name=~m/RLL_XNOR/)){
                 push @list_of_gates_original, $instance_name;}}#Do not push it if it is already a key-gate}
$instance_name="";
            
                    
                    
                   
                    
             } }   
                
        
        ####################end of paste
        
    }
    close INPUT_FH;
    #print "The original list is @list_of_gates_original\n";

    my @shuffled_indexes_false = shuffle(0..$#list_of_gates_original);

# Get just N of them.
my @pick_indexes_false = @shuffled_indexes_false[ 0 .. 64 - 1 ];  

# Pick cards from @deck
my @false_wires = @list_of_gates_original[ @pick_indexes_false ];



    my @shuffled_indexes = shuffle(0..$#list_of_gates_original);

# Get just N of them.
my @pick_indexes = @shuffled_indexes[ 0 .. 64 - 1 ];  

# Pick cards from @deck
my @picks = @list_of_gates_original[ @pick_indexes ];
print "The picks are @picks\n";
my %params = map { $_ => 1 } @picks;

   
    %Netlist_Outputs_Hash = map { $_ => 1 } @Netlist_Outputs;
     %Netlist_Inputs_Hash  = map { $_ => 1 } @Netlist_Inputs;
    #######################open file again to initialize the circuit
    local *OUTPUT_FH;    # Only way to declare a non-global filehandler
    open INPUT_FH, $input_file
      or PrintFatalError "Can't open input file '$input_file': $!!";
    while (<INPUT_FH>) {
        @ports = ();
        %ports = ();
        $line  = $_;
     ###################### lilas is pasting here
            if ( $line =~ /^\s*(module)\s+(\w+)\b/ ) {
             $module_id             = $2;
            my $full_path_output_file = "$output_dir/$output_file";
make_path($output_dir) ;
            $module_started = 1;
     
#open output file
            open OUTPUT_FH, ">$full_path_output_file"
              or PrintFatalError "Can't open the output file $full_path_output_file!";
           
            

            $header          = "";    # initialize header for a module start
           
            $body               = "";    # initialize header for a module start
            $outputs            = "";
            $module_declaration = "";

            if ( $line =~ /^.*?\;\s*$/ ) {
                chomp($line);
                $line =~ tr/)//d;
                $line =~ tr/\;//d;

                    $module_declaration          .= $line;
                 
 
                next;    # module defined on single line continue
            }
            else {       # Module is defined on more than one line

                until ( $line =~ /^.*?\;\s*$/ ) {
                    $module_declaration .= $line;
                  
                    $line = <INPUT_FH>;
                }        #End of multiline detection
                ##########
                chomp($line);
                $line =~ tr/)//d;
                $line =~ tr/\;//d;
                $module_declaration          .= $line;

                next;

            }

        }

        if ( $module_started == 0 ) {
            $directives .= $line;
            next;
        }

        if ( $line =~ /^\s*(input|wire|output|inout|reg)\s+.*/ ) {

            #Detect ports  defined on more than one line
            if ( $line =~ /^.*?\;\s*$/ ) {
                $header .= $line;
                next;    # port is defined on single line continue
            }
            else {       #port is defined on more than one line
                until ( $line =~ /^.*?\;\s*$/ ) {
                    $header .= $line;
                    $line = <INPUT_FH>;
                }        #End of multiline detection
                $header .= $line;
                next;
            }
        }


        if ( $line =~ /assign/ ) { 
        $body.=$line;
        next;
        }

        if ( $line =~ /^\s*(endmodule)\b/ ) { 
#print "this is the module $module_id\n";         
$module_declaration=~s/module\s+${module_id}\s*\(/module locked_${module_id}(/;   
	$body .= "\n" . $line;
          $count=$key_size-1; #so that I start from 0
                while ( $count >= 64 ) {
                if ($count==64)
                {
                   $module_declaration .= ", KEYINPUT" . $count.")\;\n";
                   }
                   else
                   
                   {
                    $module_declaration .= ", KEYINPUT" . $count;
                   
                   }
                   
                $count--;
                }
                
   		
                my $temp_count= $key_size-1;
                my $up_counter=64;
                while ( $up_counter <= $temp_count ) {
                    $module_declaration .=
                      "input KEYINPUT" .$up_counter. "\;\n";
                   
                    $up_counter++;
                }
             
            print OUTPUT_FH "//Secret key is'@secret_key' ..\n";
            print OUTPUT_FH "//Module:\n $module_declaration";
  
            print OUTPUT_FH "//Header:\n $header";

            print OUTPUT_FH "\n//Body:\n$body";

            next;
        }
##############In here I wanna parse the netlist. Find its inputs, its outputs, the gates..
                 
if ($line  =~ m/
	^\s*
	(\S*)  # Cell name
	\s+
	
	(\S*?)\s*?\(  #Instance Name
	.+   #ports list
	$/x
       ){
	
      if ( $line =~ /^.*?\;\s*$/ )
	{
	  
	} else {
	  until ( $line =~ /^.*?\;\s*$/ )
	    {
	  
$line =~ s/^\s+|\s+$//g;
    chomp($line);
	      $multi_line_statment .= $line;
	      $line = <INPUT_FH>;
	    }

	  $line =~ s/^\s+//g;
	  $line = $multi_line_statment.$line;
	  $multi_line_statment = "";
	  ;
	}

    }

    
    if ($line =~ m/
	^\s*
	(\S*)  # Cell name
	\s+
	
	(\S*?)\s*?\(  #Instance Name
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
push @list_of_gates, $instance_name;
            #    @ports         = split /,/, $4;

                foreach $a (@ports) {
                    $a =~ /\s*\.([A-Za-z0-9]*?)\(\s*(\S*)\s*\)/;
                    $ports{$1} = $2;
                }
                my $hash_ref = \%ports;

                my $output_name="";

                $ml_count++;
                
                ############### Gonna lock here
                my $someparam=$instance_name;
	my $edited_line="";
$edited_line=$line;
                if(exists($params{$someparam})) {


push @secret_key, $RLL_key_status;           

if (   defined($$hash_ref{"D"}) && defined($$hash_ref{"Q"})  ){

$output_name=$$hash_ref{"Q"};
$edited_line=~s/\.Q\s*\(\s*$output_name\s*\)/\.Q\(RLL_wire_A_${RLL_track_key}\)/;
$body.=$edited_line;
}

elsif (   defined($$hash_ref{"CO"}) && defined($$hash_ref{"S"})  ){


$output_name=$$hash_ref{"S"};

$edited_line=~s/\.S\s*\(\s*$output_name\s*\)/\.S\(RLL_wire_A_${RLL_track_key}\)/;
$body.=$edited_line;
}
elsif(defined($$hash_ref{"CO"})){

$output_name=$$hash_ref{"CO"};

$edited_line=~s/\.CO\s*\(\s*$output_name\s*\)/\.CO\(RLL_wire_A_${RLL_track_key}\)/;
$body.=$edited_line;

}
elsif (  defined($$hash_ref{"D"}) && !(defined($$hash_ref{"Q"}))   ){
# $body .="  $cell_name  $instance_name ( .D(".$$hash_ref{"D"}."), .CK(".$$hash_ref{"CK"}."), .QN(RLL_wire_A_$RLL_track_key) )\;\n";
$output_name=$$hash_ref{"QN"};

$edited_line=~s/\.QN\s*\(\s*$output_name\s*\)/\.QN\(RLL_wire_A_${RLL_track_key}\)/;
$body.=$edited_line;
}#DFF but without Q only QN
		    elsif (defined $$hash_ref{"Y"}){
                    $output_name=$$hash_ref{"Y"};

$edited_line=~s/\.Y\s*\(\s*$output_name\s*\)/\.Y\(RLL_wire_A_${RLL_track_key}\)/;
$body.=$edited_line;
                   # $body .="B(".$$hash_ref{"B"}."), .Y(RLL_wire_A_".$RLL_track_key.") )\;\n";
                   }



                    elsif (defined $$hash_ref{"ZN"}){
                    $output_name=$$hash_ref{"ZN"};
$edited_line=~s/\.ZN\s*\(\s*$output_name\s*\)/\.ZN\(RLL_wire_A_${RLL_track_key}\)/;
$body.=$edited_line;
                    
#$body .="B(".$$hash_ref{"B"}."), .ZN(RLL_wire_A_".$RLL_track_key.") )\;\n";
                    }
                    elsif (defined $$hash_ref{"Z"}){
                    $output_name=$$hash_ref{"Z"};
$edited_line=~s/\.Z\s*\(\s*$output_name\s*\)/\.Z\(RLL_wire_A_${RLL_track_key}\)/;
$body.=$edited_line;

                    #body .="B(".$$hash_ref{"B"}."), .Z(RLL_wire_A_".$RLL_track_key.") )\;\n";
                    }
                    
                   #}#end if B is defined within A
           if ($RLL_key_status ==1){
          #pass B
          ###Lilas Adding for MUX real locking
          if ($type==6){


$header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
$header .="wire False_wire_".$RLL_track_key."\;\n";

$body.="  INV_X1 RLL_INV_".$RLL_track_key." ( .A(RLL_wire_A_".$RLL_track_key."), .ZN(False_wire_".$RLL_track_key.") )\;\n";

$body .="  MUX2_X1 RLL_MUX_".$RLL_track_key." (.A(False_wire_${RLL_track_key}), .B(RLL_wire_A_".$RLL_track_key."), .S(KEYINPUT".$RLL_track_key."), .Z(". $output_name.") )\;\n";

          if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
 
}
        #######end of new addition MUX with K =1
                    elsif ($type==1)
          {  

my $false_wire=$false_wires[$RLL_track_key];

            $header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
        # $header .="wire RLL_wire_B_".$RLL_track_key."\;\n";
          $header .="wire RLL_gate_1o_".$RLL_track_key."\;\n";
         $header .="wire RLL_gate_2o_".$RLL_track_key."\;\n";
         $header .="wire INVERSE".$RLL_track_key."\;\n";
if($my_lib ==45){
        # $body.="  INV_X1 RLL_INV_".$RLL_track_key." ( .A(RLL_wire_A_".$RLL_track_key."), .ZN(RLL_wire_B_".$RLL_track_key.") )\;\n";
         $body.="  INV_X1 RLL_INV_".$RLL_track_key."_k ( .A(KEYINPUT".$RLL_track_key."), .ZN(INVERSE".$RLL_track_key.") )\;\n";
          $body .="  AND2_X1 RLL_gate_1_".$RLL_track_key." ( .A1(${false_wire}), .A2(INVERSE".$RLL_track_key."), .ZN(RLL_gate_1o_".$RLL_track_key.") )\;\n";
           $body .="   AND2_X1 RLL_gate_2_".$RLL_track_key." ( .A1(RLL_wire_A_".$RLL_track_key."), .A2(KEYINPUT".$RLL_track_key."), .ZN(RLL_gate_2o_".$RLL_track_key.") )\;\n";
            $body .="  OR2_X1 RLL_OR_".$RLL_track_key." (.A1(RLL_gate_1o_".$RLL_track_key."), .A2(RLL_gate_2o_".$RLL_track_key."), .ZN(". $output_name.") )\;\n";
        }
else{
#TODO

         $body.="  INV_X1M_A9TH RLL_INV_".$RLL_track_key."_k ( .A(KEYINPUT".$RLL_track_key."), .Y(INVERSE".$RLL_track_key.") )\;\n";
          $body .="  AND2_X2M_A9TH RLL_gate_1_".$RLL_track_key." ( .A(${false_wire}), .B(INVERSE".$RLL_track_key."), .Y(RLL_gate_1o_".$RLL_track_key.") )\;\n";
           $body .="   AND2_X2M_A9TH RLL_gate_2_".$RLL_track_key." ( .A(RLL_wire_A_".$RLL_track_key."), .B(KEYINPUT".$RLL_track_key."), .Y(RLL_gate_2o_".$RLL_track_key.") )\;\n";
            $body .="  OR2_X1M_A9TH RLL_OR_".$RLL_track_key." (.A(RLL_gate_1o_".$RLL_track_key."), .B(RLL_gate_2o_".$RLL_track_key."), .Y(". $output_name.") )\;\n";
}
	 if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
           
          }
          elsif ($type==2)
          {
            $header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
         $header .="wire RLL_wire_B_".$RLL_track_key."\;\n";
          $header .="wire RLL_gate_1o_".$RLL_track_key."\;\n";
         $header .="wire RLL_gate_2o_".$RLL_track_key."\;\n";
         $header .="wire INVERSE".$RLL_track_key."\;\n";
         $body.="  INV_X1 RLL_INV_".$RLL_track_key." ( .A(RLL_wire_A_".$RLL_track_key."), .ZN(RLL_wire_B_".$RLL_track_key.") )\;\n";
         $body.="  INV_X1 RLL_INV_".$RLL_track_key."_k ( .A(KEYINPUT".$RLL_track_key."), .ZN(INVERSE".$RLL_track_key.") )\;\n";
                    $body .="  NAND2_X1 RLL_gate_1_".$RLL_track_key." ( .A1(RLL_wire_B_".$RLL_track_key."), .A2(INVERSE".$RLL_track_key."), .ZN(RLL_gate_1o_".$RLL_track_key.") )\;\n";
           $body .="   NAND2_X1 RLL_gate_2_".$RLL_track_key." ( .A1(RLL_wire_A_".$RLL_track_key."), .A2(KEYINPUT".$RLL_track_key."), .ZN(RLL_gate_2o_".$RLL_track_key.") )\;\n";
            $body .="  NAND2_X1 RLL_NAND_".$RLL_track_key." (.A1(RLL_gate_1o_".$RLL_track_key."), .A2(RLL_gate_2o_".$RLL_track_key."), .ZN(". $output_name.") )\;\n";
               
           if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
         
          }
                     elsif ($type==3)
          {  
            $header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
         $header .="wire RLL_wire_B_".$RLL_track_key."\;\n";
          $header .="wire RLL_gate_1o_".$RLL_track_key."\;\n";
         $header .="wire RLL_gate_2o_".$RLL_track_key."\;\n";
         $header .="wire INVERSE".$RLL_track_key."\;\n";
         $body.="  INV_X1 RLL_INV_".$RLL_track_key." ( .A(RLL_wire_A_".$RLL_track_key."), .ZN(RLL_wire_B_".$RLL_track_key.") )\;\n";
         $body.="  INV_X1 RLL_INV_".$RLL_track_key."_k ( .A(KEYINPUT".$RLL_track_key."), .ZN(INVERSE".$RLL_track_key.") )\;\n";
          $body .="  NOR2_X1 RLL_gate_1_".$RLL_track_key." ( .A1(RLL_wire_B_".$RLL_track_key."), .A2(KEYINPUT".$RLL_track_key."), .ZN(RLL_gate_1o_".$RLL_track_key.") )\;\n";
           $body .="   NOR2_X1 RLL_gate_2_".$RLL_track_key." ( .A1(RLL_wire_A_".$RLL_track_key."), .A2(INVERSE".$RLL_track_key."), .ZN(RLL_gate_2o_".$RLL_track_key.") )\;\n";
            $body .="  NOR2_X1 RLL_OR_".$RLL_track_key." (.A1(RLL_gate_1o_".$RLL_track_key."), .A2(RLL_gate_2o_".$RLL_track_key."), .ZN(". $output_name.") )\;\n";
          if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
           
          }
           elsif ($type==4)
          {
		$header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
if ($my_lib == 65){



 $body .="XNOR2_X1M_A9TH RLL_XNOR_".$RLL_track_key." (.A(RLL_wire_A_".$RLL_track_key."), .B(KEYINPUT".$RLL_track_key."), .Y(". $output_name.") )\;\n";

}
else{
   $body .="  XNOR2_X1 RLL_XNOR_".$RLL_track_key." (.A(RLL_wire_A_".$RLL_track_key."), .B(KEYINPUT".$RLL_track_key."), .ZN(". $output_name.") )\;\n";
     }    
               
           if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
         
          }
                     elsif ($type==5)
          {
$header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
                   $body .="  AND2_X1 RLL_AND_".$RLL_track_key." (.A1(RLL_wire_A_".$RLL_track_key."), .A2(KEYINPUT".$RLL_track_key."), .ZN(". $output_name.") )\;\n";
          
               
           if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
        
          }
         
   #todo        $body .="  XOR RLL_XOR_".$RLL_track_key." (.A(RLL_wire_".$RLL_track_key."), .B(KEYINPUT".$RLL_track_key."), .Y(RLL_Inv_wire".$RLL_track_key.") )\;\n";
   #todo        $header .="wire RLL_Inv_wire".$RLL_track_key."\;\n";
          
     #todo      $body .="  NOT RLL_NOT_".$RLL_track_key." (.A(RLL_Inv_wire".$RLL_track_key."), .Y(".$$hash_ref{"Y"}.") )\;\n";
       

 $RLL_key_status =$x[rand @x];
 #  $RLL_key_status=0;
          }else{
         
           #todo          $body .="  XOR RLL_XOR_".$RLL_track_key." (.A(RLL_wire_".$RLL_track_key."), .B(KEYINPUT".$RLL_track_key."), .Y(".$$hash_ref{"Y"}.") )\;\n";
           #pass A
          if ($type==6){


$header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
$header .="wire False_wire_".$RLL_track_key."\;\n";
$body.="  INV_X1 RLL_INV_".$RLL_track_key." ( .A(RLL_wire_A_".$RLL_track_key."), .ZN(False_wire_".$RLL_track_key.") )\;\n";

$body .="  MUX2_X1 RLL_MUX_".$RLL_track_key." (.A(RLL_wire_A_${RLL_track_key}), .B(False_wire_".$RLL_track_key."), .S(KEYINPUT".$RLL_track_key."), .Z(". $output_name.") )\;\n";

          if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
 
}
         elsif ($type==1)
          {
 
	my $false_wire=$false_wires[$RLL_track_key];

	 $header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
     #   $header .="wire RLL_wire_B_".$RLL_track_key."\;\n";
          $header .="wire RLL_gate_1o_".$RLL_track_key."\;\n";
         $header .="wire RLL_gate_2o_".$RLL_track_key."\;\n";
         $header .="wire INVERSE".$RLL_track_key."\;\n";
if ($my_lib==45){
      #  $body.="  INV_X1 RLL_INV_".$RLL_track_key." ( .A(RLL_wire_A_".$RLL_track_key."), .ZN(RLL_wire_B_".$RLL_track_key.") )\;\n";
         $body.="  INV_X1 RLL_INV_".$RLL_track_key."_k ( .A(KEYINPUT".$RLL_track_key."), .ZN(INVERSE".$RLL_track_key.") )\;\n";
            $body .="  AND2_X1 RLL_gate_1_".$RLL_track_key." ( .A1(${false_wire}), .A2(KEYINPUT".$RLL_track_key."), .ZN(RLL_gate_1o_".$RLL_track_key.") )\;\n";
           $body .="   AND2_X1 RLL_gate_2_".$RLL_track_key." ( .A1(RLL_wire_A_".$RLL_track_key."), .A2(INVERSE".$RLL_track_key."), .ZN(RLL_gate_2o_".$RLL_track_key.") )\;\n";
            $body .="  OR2_X1 RLL_OR_".$RLL_track_key." (.A1(RLL_gate_1o_".$RLL_track_key."), .A2(RLL_gate_2o_".$RLL_track_key."), .ZN(". $output_name.") )\;\n";
}
else{

         $body.="  INV_X1M_A9TH RLL_INV_".$RLL_track_key."_k ( .A(KEYINPUT".$RLL_track_key."), .Y(INVERSE".$RLL_track_key.") )\;\n";
            $body .="  AND2_X2M_A9TH RLL_gate_1_".$RLL_track_key." ( .A(${false_wire}), .B(KEYINPUT".$RLL_track_key."), .Y(RLL_gate_1o_".$RLL_track_key.") )\;\n";
           $body .="   AND2_X2M_A9TH RLL_gate_2_".$RLL_track_key." ( .A(RLL_wire_A_".$RLL_track_key."), .B(INVERSE".$RLL_track_key."), .Y(RLL_gate_2o_".$RLL_track_key.") )\;\n";
            $body .="  OR2_X1M_A9TH RLL_OR_".$RLL_track_key." (.A(RLL_gate_1o_".$RLL_track_key."), .B(RLL_gate_2o_".$RLL_track_key."), .Y(". $output_name.") )\;\n";
#TODO
}         
 if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
          
          }
          elsif ($type==2)
          {  $header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
         $header .="wire RLL_wire_B_".$RLL_track_key."\;\n";
          $header .="wire RLL_gate_1o_".$RLL_track_key."\;\n";
         $header .="wire RLL_gate_2o_".$RLL_track_key."\;\n";
         $header .="wire INVERSE".$RLL_track_key."\;\n";
         $body.="  INV_X1 RLL_INV_".$RLL_track_key." ( .A(RLL_wire_A_".$RLL_track_key."), .ZN(RLL_wire_B_".$RLL_track_key.") )\;\n";
         $body.="  INV_X1 RLL_INV_".$RLL_track_key."_k ( .A(KEYINPUT".$RLL_track_key."), .ZN(INVERSE".$RLL_track_key.") )\;\n";
                  if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
                       $body .="  NAND2_X1 RLL_gate_1_".$RLL_track_key." ( .A1(RLL_wire_B_".$RLL_track_key."), .A2(KEYINPUT".$RLL_track_key."), .ZN(RLL_gate_1o_".$RLL_track_key.") )\;\n";
           $body .="   NAND2_X1 RLL_gate_2_".$RLL_track_key." ( .A1(RLL_wire_A_".$RLL_track_key."), .A2(INVERSE".$RLL_track_key."), .ZN(RLL_gate_2o_".$RLL_track_key.") )\;\n";
            $body .="  NAND2_X1 RLL_OR_".$RLL_track_key." (.A1(RLL_gate_1o_".$RLL_track_key."), .A2(RLL_gate_2o_".$RLL_track_key."), .ZN(". $output_name.") )\;\n";
          }
          elsif ($type==3)
          {  $header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
         $header .="wire RLL_wire_B_".$RLL_track_key."\;\n";
          $header .="wire RLL_gate_1o_".$RLL_track_key."\;\n";
         $header .="wire RLL_gate_2o_".$RLL_track_key."\;\n";
         $header .="wire INVERSE".$RLL_track_key."\;\n";
         $body.="  INV_X1 RLL_INV_".$RLL_track_key." ( .A(RLL_wire_A_".$RLL_track_key."), .ZN(RLL_wire_B_".$RLL_track_key.") )\;\n";
         $body.="  INV_X1 RLL_INV_".$RLL_track_key."_k ( .A(KEYINPUT".$RLL_track_key."), .ZN(INVERSE".$RLL_track_key.") )\;\n";
            $body .="  NOR2_X1 RLL_gate_1_".$RLL_track_key." ( .A1(RLL_wire_B_".$RLL_track_key."), .A2(INVERSE".$RLL_track_key."), .ZN(RLL_gate_1o_".$RLL_track_key.") )\;\n";
           $body .="   NOR2_X1 RLL_gate_2_".$RLL_track_key." ( .A1(RLL_wire_A_".$RLL_track_key."), .A2(KEYINPUT".$RLL_track_key."), .ZN(RLL_gate_2o_".$RLL_track_key.") )\;\n";
            $body .="  NOR2_X1 RLL_OR_".$RLL_track_key." (.A1(RLL_gate_1o_".$RLL_track_key."), .A2(RLL_gate_2o_".$RLL_track_key."), .ZN(". $output_name.") )\;\n";
          if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
          
          }
           elsif ($type==4)
          {  $header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
if ($my_lib == 65){

$body .=" XOR2_X1M_A9TH RLL_XOR_".$RLL_track_key." (.A(RLL_wire_A_".$RLL_track_key."), .B(KEYINPUT".$RLL_track_key."), .Y(". $output_name.") )\;\n";

}else{
                    $body .="  XOR2_X1 RLL_XOR_".$RLL_track_key." (.A(RLL_wire_A_".$RLL_track_key."), .B(KEYINPUT".$RLL_track_key."), .Z(". $output_name.") )\;\n";
      }         
           if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
         
          }
         elsif ($type==5)
          {
$header .="wire RLL_wire_A_".$RLL_track_key."\;\n";
                   $body .="  OR2_X1 RLL_OR_".$RLL_track_key." (.A1(RLL_wire_A_".$RLL_track_key."), .A2(KEYINPUT".$RLL_track_key."), .ZN(". $output_name.") )\;\n";
          
               
           if ($vary==1)
          {  $type = $a[ rand @a ];

        
          }
         
          }
          
         # $RLL_key_status=1;


 $RLL_key_status =$x[rand @x];
}
          
          $RLL_track_key++;
                
                
                }#end of I need to lock or not
                 else{ $body .= $line;}
                
                
                
                
                
                
                
                #############end of added locking
               
                    
             }       
                
            

        

    }    #######end of opening file again
    close INPUT_FH;
    ############################






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

sub PrintDebug {
    my $orig_list_separator = $";
    $" =
      ',';   # To print with separator, @some_list must be outside double-quotes
    warn "DEBUG: ", (caller)[2], ": @_\n" if ($debug);
    $" = $orig_list_separator;    # Dummy " for perl-mode in Emacs
}



__END__

