********
APIISIM
********

Presentation
============

The aim of this project is to make a service that provides trip planning between multiple heterogeneous multi-modal information systems (MIS).
This means calculating trips between different regions and/or countries, something that is currently very difficult. Indeed, each MIS having its own API and conventions, they act like closed systems with no interaction between them.

To reach our goal, we need to create generic APIs and conventions that will be shared by all components (both clients and services). 
This implies:

    - Defining a generic API for all MISes
    - Defining a generic API for the trip planner

Architecture overview
=====================

This project is divided into several components:

    #. The Metabase which consists in a database storing all required information to compute trips:
    
        - List of MISes with some info (supported transport modes, connected MISes...).
        - List of all stop points, each one being identified by a MIS id and a stop code (unique inside its MIS).
        - List of all transfers. A transfer can be viewed as a link between two MISes. When we want to go from a MIS to another one, we always do it via a transfer. It is composed by 2 stop points, one in each MIS.

    #. The Back Office which manages the database, it performs the following tasks:

        - Retrieve all stops points from all MISes
        - Compute transfers by looking at stop points that are within a specified distance so that they can be used to switch between two MISes.
        - Compute MIS connections which basically consists in looking for MISes that can be linked together via transfers.

    #. The MIS translator: Web service that translates the generic API into MIS specific APIs. It acts as an abstraction layer for both the Back Office and the Meta Planner to make them communicate with different MISes via a unique API.
    #. The Meta Planner: Web service that provides an API to compute trip plannings within all avalaible MISes, this is the only component that the final user web client will communicate with.


