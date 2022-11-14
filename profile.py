#!/usr/bin/python

"""This profile allows the allocation of resources for over-the-air operation on
the POWDER platform. Specifically, the profile has options to request the
allocation of software defined radios (SDRs) in rooftop base-stations and
fixed-endpoints (i.e., nodes deployed at human height).

*IMPORTANT NOTE:* Due to the ongoing volatility with spectrum access
for outdoor over the air resouces at POWDER, this profile may not work
well or at all.  Originally this profile targeted band 7 and POWDER
radios had maching band 7 RF front-ends to provide the necessary SNR
for 4G/5G communications. POWDER no longer has access to band 7 due to
3rd party incumbents. Please ask on the POWDER Users list for current
status.

Map of deployment is here:
https://www.powderwireless.net/map

The base-station SDRs are X310s and connected to an antenna covering the
cellular band (1695 - 2690 MHz), i.e., cellsdr, or to an antenna covering the
CBRS band (3400 - 3800 MHz), i.e., cbrssdr. Each X310 is paired with a compute
node (by default a Dell d740).

The fixed-endpoint SDRs are B210s each of which is paired with an Intel NUC
small form factor compute node. Both B210s are connected to broadband antennas:
nuc1 is connected in an RX only configuration, while nuc2 is connected in a
TX/RX configuration.

This profile uses a disk image with srsLTE and UHD pre-installed, with an option
for including the srsLTE source code.

Resources needed to realize a basic srsLTE setup consisting of a UE, an eNodeB
and an EPC core network:

  * Spectrum for LTE FDD opperation (uplink and downlink).
  * A "nuc2" fixed-endpoint compute/SDR pair (This will run the UE side.)
  * A "cellsdr" base station SDR. (This will be the radio side of the eNodeB.)
  * A "d740" compute node. (This will run both the eNodeB software and the EPC software.)
  
**Example resources that can be used (and that need to be reserved before
  instantiating the profile):**

  * Hardware (at least one set of resources are needed):
   * WEB, nuc2; Emulab, cellsdr1-browning; Emulab, d740
   * Bookstore, nuc2; Emulab, cellsdr1-browning; Emulab, d740
   * WEB, nuc2; Emulab, cellsdr1-meb; Emulab, d740
  * Spectrum:
   * Uplink: 2500 MHz to 2510 MHz
   * Downlink: 2620 MHz to 2630 MHz

The instuctions below assume the first hardware configuration.

Instructions:

**IMPORTANT: You MUST adjust the configuration of srsLTE eNodeB and UE
components if you changed the frequency ranges in the profile
parameters. Do so BEFORE starting any srsLTE processes!  Please see
instructions further on.**

These instructions assume the following hardware set was selected when the
profile was instantiated:

 * WEB, nuc2; Emulab, cellsdr1-browning; Emulab, d740

#### To run the srsLTE software

**To run the EPC**

Open a terminal on the `cellsdr1-browning-comp` node in your experiment. (Go to
the "List View" in your experiment. If you have ssh keys and an ssh client
working in your setup you should be able to click on the black "ssh -p ..."
command to get a terminal. If ssh is not working in your setup, you can open a
browser shell by clicking on the Actions icon corresponding to the node and
selecting Shell from the dropdown menu.)

Start up the EPC:

    sudo srsepc
    
**To run the eNodeB**

Open another terminal on the `cellsdr1-browning-comp` node in your experiment.

Adjust the frequencies to use, if necessary (*MANDATORY* if you have changed these in the profile parameters):

  * Open `/etc/srslte/enb.conf`
  * Find `dl_earfcn` and comment it out
  * Add `dl_freq` and set to the center frequency for the downlink channel you allocated
    * E.g., `dl_freq = 2625e6` if your downlink channel is 2620 - 2630 MHz
  * Add `ul_freq` and set to the center frequency for the uplink channel you allocated
    * E.g., `ul_freq = 2505e6` if your uplink channel is 2500 - 2510 MHz

Start up the eNodeB:

    sudo srsenb

**To run the UE**

Open a terminal on the `b210-web-nuc2` node in your experiment.

Adjust the frequencies to use, if necessary (*MANDATORY* if you have changed these in the profile parameters):

  * Open `/etc/srslte/ue.conf`
  * Find `dl_earfcn` and comment it out
  * Add `dl_freq` and set to the center frequency for the downlink channel you allocated
    * E.g., `dl_freq = 2625e6` if your downlink channel is 2620 - 2630 MHz
  * Add `ul_freq` and set to the center frequency for the uplink channel you allocated
    * E.g., `ul_freq = 2505e6` if your uplink channel is 2500 - 2510 MHz

Start up the UE:

    sudo srsue

**Verify functionality**

Open another terminal on the `b210-web-nuc2` node in your experiment.

Verify that the virtual network interface tun_srsue" has been created:

    ifconfig tun_srsue

Run ping to the SGi IP address via your RF link:
    
    ping 172.16.0.1

Killing/restarting the UE process will result in connectivity being interrupted/restored.

If you are using an ssh client with X11 set up, you can run the UE with the GUI
enabled to see a real time view of the signals received by the UE:

    sudo srsue --gui.enable 1

#### Troubleshooting

**No compatible RF-frontend found**

If srsenb fails with an error indicating "No compatible RF-frontend found",
you'll need to flash the appropriate firmware to the X310 and power-cycle it
using the portal UI. Run `uhd_usrp_probe` in a shell on the associated compute
node to get instructions for downloading and flashing the firmware. Use the
Action buttons in the List View tab of the UI to power cycle the appropriate
X310 after downloading and flashing the firmware. If srsue fails with a similar
error, try power-cycling the associated NUC.

**UE can't sync with eNB**

If you find that the UE cannot sync with the eNB, passing
`--phy.force_ul_amplitude 1.0` to srsue may help. You may have to rerun srsue a
few times to get it to sync.

"""

import geni.portal as portal
import geni.rspec.pg as rspec
import geni.rspec.emulab.pnext as pn
import geni.rspec.igext as ig
import geni.rspec.emulab.spectrum as spectrum

class GLOBALS:
    SRSLTE_IMG = "urn:publicid:IDN+emulab.net+image+PowderTeam:U18LL-SRSLTE"
    SRSLTE_SRC_DS = "urn:publicid:IDN+emulab.net:powderteam+imdataset+srslte-src-v19"
    DLDEFLOFREQ = 2620.0
    DLDEFHIFREQ = 2630.0
    ULDEFLOFREQ = 2500.0
    ULDEFHIFREQ = 2510.0


def x310_node_pair(idx, x310_radio):
    radio_link = request.Link("radio-link-%d" % (idx))
    radio_link.bandwidth = 10*1000*1000

    node = request.RawPC("%s-comp" % (x310_radio.radio_name))
    node.hardware_type = params.x310_pair_nodetype
    node.disk_image = GLOBALS.SRSLTE_IMG
    node.component_manager_id = "urn:publicid:IDN+emulab.net+authority+cm"
    node.addService(rspec.Execute(shell="bash", command="/local/repository/bin/add-nat-and-ip-forwarding.sh"))
    node.addService(rspec.Execute(shell="bash", command="/local/repository/bin/update-config-files.sh"))
    node.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-cpu.sh"))
    node.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-sdr-iface.sh"))

    if params.include_srslte_src:
        bs = node.Blockstore("bs-comp-%s" % idx, "/opt/srslte")
        bs.dataset = GLOBALS.SRSLTE_SRC_DS

    node_radio_if = node.addInterface("usrp_if")
    node_radio_if.addAddress(rspec.IPv4Address("192.168.40.1",
                                               "255.255.255.0"))
    radio_link.addInterface(node_radio_if)

    radio = request.RawPC("%s-x310" % (x310_radio.radio_name))
    radio.component_id = x310_radio.radio_name
    radio.component_manager_id = "urn:publicid:IDN+emulab.net+authority+cm"
    radio_link.addNode(radio)


def b210_nuc_pair(idx, b210_node):
    b210_nuc_pair_node = request.RawPC("b210-%s-%s" % (b210_node.aggregate_id, "nuc2"))
    agg_full_name = "urn:publicid:IDN+%s.powderwireless.net+authority+cm" % (b210_node.aggregate_id)
    b210_nuc_pair_node.component_manager_id = agg_full_name
    b210_nuc_pair_node.component_id = "nuc2"
    b210_nuc_pair_node.disk_image = GLOBALS.SRSLTE_IMG
    b210_nuc_pair_node.addService(rspec.Execute(shell="bash", command="/local/repository/bin/update-config-files.sh"))
    b210_nuc_pair_node.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-cpu.sh"))

    if params.include_srslte_src:
        bs = b210_nuc_pair_node.Blockstore("bs-nuc-%s" % idx, "/opt/srslte")
        bs.dataset = GLOBALS.SRSLTE_SRC_DS


portal.context.defineParameter("include_srslte_src",
                               "Include srsLTE source code.",
                               portal.ParameterType.BOOLEAN,
                               False)

node_type = [
    ("d740",
     "Emulab, d740"),
    ("d430",
     "Emulab, d430")
]

portal.context.defineParameter("x310_pair_nodetype",
                               "Type of compute node paired with the X310 Radios",
                               portal.ParameterType.STRING,
                               node_type[0],
                               node_type)

rooftop_names = [
    ("cellsdr1-browning",
     "Emulab, cellsdr1-browning (Browning)"),
    ("cellsdr1-bes",
     "Emulab, cellsdr1-bes (Behavioral)"),
    ("cellsdr1-dentistry",
     "Emulab, cellsdr1-dentistry (Dentistry)"),
    ("cellsdr1-fm",
     "Emulab, cellsdr1-fm (Friendship Manor)"),
    ("cellsdr1-honors",
     "Emulab, cellsdr1-honors (Honors)"),
    ("cellsdr1-meb",
     "Emulab, cellsdr1-meb (MEB)"),
    ("cellsdr1-smt",
     "Emulab, cellsdr1-smt (SMT)"),
    ("cellsdr1-hospital",
     "Emulab, cellsdr1-hospital (Hospital)"),
    ("cellsdr1-ustar",
     "Emulab, cellsdr1-ustar (USTAR)"),
]

portal.context.defineStructParameter("x310_radios", "X310 Radios", [],
                                     multiValue=True,
                                     itemDefaultValue={},
                                     min=0, max=None,
                                     members=[
                                        portal.Parameter(
                                             "radio_name",
                                             "Rooftop base-station X310",
                                             portal.ParameterType.STRING,
                                             rooftop_names[0],
                                             rooftop_names)
                                     ])

fixed_endpoint_aggregates = [
    ("web",
     "WEB, nuc2"),
    ("bookstore",
     "Bookstore, nuc2"),
    ("humanities",
     "Humanities, nuc2"),
    ("law73",
     "Law 73, nuc2"),
    ("ebc",
     "EBC, nuc2"),
    ("madsen",
     "Madsen, nuc2"),
    ("sagepoint",
     "Sage Point, nuc2"),
    ("moran",
     "Moran, nuc2"),
    ("cpg",
     "Central Parking Garage, nuc2"),
    ("guesthouse",
     "Guest House, nuc2"),
]

portal.context.defineStructParameter("b210_nodes", "B210 Radios", [],
                                     multiValue=True,
                                     min=0, max=None,
                                     members=[
                                         portal.Parameter(
                                             "aggregate_id",
                                             "Fixed Endpoint B210",
                                             portal.ParameterType.STRING,
                                             fixed_endpoint_aggregates[0],
                                             fixed_endpoint_aggregates)  # List of LegalValue
                                     ],)


portal.context.defineParameter(
    "ul_freq_min",
    "Uplink Frequency Min",
    portal.ParameterType.BANDWIDTH,
    GLOBALS.ULDEFLOFREQ,
    longDescription="Values are rounded to the nearest kilohertz."
)
portal.context.defineParameter(
    "ul_freq_max",
    "Uplink Frequency Max",
    portal.ParameterType.BANDWIDTH,
    GLOBALS.ULDEFHIFREQ,
    longDescription="Values are rounded to the nearest kilohertz."
)
portal.context.defineParameter(
    "dl_freq_min",
    "Downlink Frequency Min",
    portal.ParameterType.BANDWIDTH,
    GLOBALS.DLDEFLOFREQ,
    longDescription="Values are rounded to the nearest kilohertz."
)
portal.context.defineParameter(
    "dl_freq_max",
    "Downlink Frequency Max",
    portal.ParameterType.BANDWIDTH,
    GLOBALS.DLDEFHIFREQ,
    longDescription="Values are rounded to the nearest kilohertz."
)

# Bind parameters
params = portal.context.bindParameters()

# Check frequency parameters.
if params.ul_freq_min < 2500 or params.ul_freq_min > 2570 \
   or params.ul_freq_max < 2500 or params.ul_freq_max > 2570:
    perr = portal.ParameterError("Band 7 uplink frequencies must be between 2500 and 2570 MHz", ['ul_freq_min', 'ul_freq_max'])
    portal.context.reportError(perr)
if params.ul_freq_max - params.ul_freq_min < 1:
    perr = portal.ParameterError("Minimum and maximum frequencies must be separated by at least 1 MHz", ['ul_freq_min', 'ul_freq_max'])
    portal.context.reportError(perr)
if params.dl_freq_min < 2620 or params.dl_freq_min > 2690 \
   or params.dl_freq_max < 2620 or params.dl_freq_max > 2690:
    perr = portal.ParameterError("Band 7 downlink frequencies must be between 2620 and 2690 MHz", ['dl_freq_min', 'dl_freq_max'])
    portal.context.reportError(perr)
if params.dl_freq_max - params.dl_freq_min < 1:
    perr = portal.ParameterError("Minimum and maximum frequencies must be separated by at least 1 MHz", ['dl_freq_min', 'dl_freq_max'])
    portal.context.reportError(perr)
    
# Now verify.
portal.context.verifyParameters()

# Lastly, request resources.
request = portal.context.makeRequestRSpec()

for i, x310_radio in enumerate(params.x310_radios):
    x310_node_pair(i, x310_radio)

for i, b210_node in enumerate(params.b210_nodes):
    b210_nuc_pair(i, b210_node)

request.requestSpectrum(params.ul_freq_min, params.ul_freq_max, 0)
request.requestSpectrum(params.dl_freq_min, params.dl_freq_max, 0)
    
portal.context.printRequestRSpec()