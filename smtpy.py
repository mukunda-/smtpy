# smtpy
# 
# - A neat tool to test SMTP submission.
#
# Copyright (c) 2021 Mukunda Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT
# OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#/////////////////////////////////////////////////////////////////////////////////////////
import smtplib, uuid, os, re, traceback, argparse, dns.resolver
from email import utils

VERSION = "v1.1.1"

VarSubs = {}

#/////////////////////////////////////////////////////////////////////////////////////////
def Main():
   print( "---------------------------" )
   print( f"## smtpy {VERSION}" )
   args = ParseArgs()
   for i in range( 0, len(args.arg), 2 ):
      VarSubs[args.arg[i]] = args.arg[i+1]
   inputfile = args.inputfile
   CheckInputFileExists( inputfile )
   SendMail( inputfile )

#-----------------------------------------------------------------------------------------
def ParseArgs():
   parser = argparse.ArgumentParser( description="Deliver an email to an SMTP server." )
   parser.add_argument( "inputfile", help="Smtpyfile. See template." )
   parser.add_argument( "--arg", "-a",
      metavar=("NAME","VAL"), action="extend", default=[], nargs=2, type=str,
      help="For example, `--arg var 5`, to replace {{var}} in the smptyfile." )
   return parser.parse_args()

#-----------------------------------------------------------------------------------------
def CheckInputFileExists( inputfile ):
   if not inputfile or not os.path.exists( inputfile ):
      print( "Input file doesn't exist." )
      exit( -1 )

#-----------------------------------------------------------------------------------------
def ExtractEmails( line ):
   return re.findall( r"[^\s<]+@[^\s>]+", line )
   
#-----------------------------------------------------------------------------------------
def ExtractEmail( line ):
   a = re.findall( r"[^\s<]+@[^\s>]+", line )
   if len(a) > 0:
      return a[0]
   else:
      return None

#-----------------------------------------------------------------------------------------
def ExtractDomain( email ):
   return email.split( "@" )[1]

#-----------------------------------------------------------------------------------------
def SplitHeader( line ):
   line = line.split( ":", 1 )
   header = line[0].strip()
   value = ""
   if len(line) > 1:
      value = line[1].strip()
   return (header, value)

#-----------------------------------------------------------------------------------------
def StripNewlines( line ):
   return line.replace("\r", "").replace("\n", "")

def InsertVariables_ReplaceFunc( match ):
   return VarSubs.get( x[1], "" )

def InsertVariables( line ):
   return re.sub( r"{{(.*?)}}", InsertVariables_ReplaceFunc, line )

#-----------------------------------------------------------------------------------------
def SendMail( inputfile ):

   helo_domain     = None
   host            = None
   port            = 25
   mailfrom        = None
   rcpt            = []
   payload         = []
   payload_headers = []
   options         = {}
   has_from        = False
   has_to          = False
   has_date        = False
   has_message_id  = False
   username        = None
   password        = ""
   errors          = 0
   
   with open( inputfile, "r", encoding="utf-8" ) as f:
      for line in f:
         line = re.sub( r"#.*", "", line )
         line = line.strip()
         line = InsertVariables(line)
         if line == "": continue
         if line.startswith("---"): break

         (header, line) = SplitHeader( line )
         header = header.lower()
         
         if header == "from":
            mailfrom = line
         elif header == "to":
            rcpt.extend( [s.strip() for s in line.split(",")] )
         elif header == "helo":
            helo_domain = line
         elif header == "user":
            username = line
         elif header == "password":
            password = line
         elif header == "host":
            host = line
         elif header == "port":
            port = int(line)
         elif header == "options":
            for option in [a.strip() for a in line.split(",")]:
               options[option] = True
            pass
         else:
            print( f"*** Error: unknown directive - {header}" )
            errors += 1

      for line in f:
         line = StripNewlines(line)
         line = InsertVariables(line)
         if line == "": break
         payload_headers.append( line )
         (header, line) = SplitHeader( line )
         header = header.lower()

         if header == "from":
            if not mailfrom:
               mailfrom = ExtractEmail( line )
            has_from = True
         elif header == "to" or header == "cc" or header == "bcc":
            if len(rcpt) == 0:
               rcpt.extend( ExtractEmails(line) )
            has_to = True
         elif header == "date":
            has_date = True
         elif header == "message-id":
            has_message_id = True
      
      for line in f:
         payload.append( InsertVariables(StripNewlines(line)) )
   
   if not mailfrom:
      print( "*** Error: missing MAIL FROM." )
      errors += 1

   if not helo_domain:
      helo_domain = ExtractDomain( mailfrom )
   
   if len(rcpt) == 0:
      print( "*** Error: missing recipients." )
      errors += 1

   if not host:
      # Try to resolve.
      domain = ExtractDomain( rcpt[0] )
      print( "No host specified." )
      print( f"Looking up MX records for {domain}." )
      try:
         results = dns.resolver.resolve( domain, "MX" )
         host = str(results[0].exchange)

         if host == "" or host == ".":
            print( "No record found." )
            host = None
         else:
            print( f"Host set to \"{host}\"." )
      except dns.resolver.NXDOMAIN:
         print( "Couldn't query domain:", domain )

   if not host:
      print( "*** Error: missing HOST." )
      errors += 1
   
   if not has_from and not options.get("nofromto"):
      payload_headers.append( f"From: {mailfrom}" )
      print( "Adding From field to payload." )
   
   if not has_to and not options.get("nofromto"):
      payload_headers.append( f"To: {', '.join(rcpt)}" )
      print( "Adding To field to payload." )

   if not has_date and not options.get("nodate"):
      payload_headers.append( f"Date: {utils.formatdate()}")
      print( "Adding Date field to payload." )

   if not has_message_id and not options.get("nomessageid"):
      msgid = f"<{str(uuid.uuid4())}@{ExtractDomain(mailfrom)}>"
      payload_headers.append( f"Message-ID: {msgid}" )
      print( "Adding Message-ID to payload.", msgid )

   payload = "\r\n".join(payload_headers) + "\r\n\r\n" + "\r\n".join(payload)

   print( "Ready to submit." )
   
   if errors > 0:
      print( f"{errors} errors have occurred. Please fix them and retry." )
      exit( -1 )

   print( "Connecting to", host, "on port", port )
   with smtplib.SMTP( host, port ) as smtp:
      print( ">> EHLO", helo_domain )
      smtp.ehlo( helo_domain )

      if options.get("tls"):
         print( ">> STARTTLS" )
         smtp.starttls()
         smtp.ehlo( helo_domain )
         
      if username:
         print( ">> LOGIN", username )
         smtp.login( username, password )

      print( ">> MAIL FROM:", mailfrom )
      print( ">> RCPT TO:", ", ".join(rcpt) )
      print( "--- DATA ---" )
      print( payload[0:10000] )
      if len(payload) > 10000:
         print( "...<truncated payload at 10000 bytes>..." )
      print( "------------" )
      smtp.sendmail( mailfrom, rcpt, payload.encode("utf-8") )
   
   print( "Mail submitted!" )
   print( "---------------" )

if __name__ == "__main__": Main()
#/////////////////////////////////////////////////////////////////////////////////////////