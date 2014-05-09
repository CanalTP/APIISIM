# List of enabled Mis APIs modules
MIS_APIS_AVAILABLE = frozenset(["dummy", "navitia", "test1", "test2"])
mis_api_mapping = {} # Mis name : MisApi Class

"""
Load all available Mis APIs modules and populate mis_api_mapping dict so that
we can easily instanciate a MisApi object based on the Mis name.
"""
def load_mis_apis():
    for m in MIS_APIS_AVAILABLE:
        mis_module = "%s_module" % m
        exec ("import mis_api.%s as %s" % (m, mis_module))
        mis_name = eval("%s.NAME" % mis_module)
        mis_api_mapping[mis_name] = eval("%s.MisApi" % mis_module)

"""
Return new MisApi object based on given mis_name.
"""
def get_mis_api(mis_name):
    if mis_api_mapping.has_key(mis_name):
        return mis_api_mapping[mis_name]()
    else:
        return None
