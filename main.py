import xml.etree.ElementTree as ET
from rdflib import Graph, Literal, RDF, URIRef, Namespace, XSD
from rdflib.namespace import SOSA

class robot_graph():
    def __init__(self, model_path) -> None:
        # URDF model related variables
        self.model = ET.parse(model_path)
        self.model_root = self.model.getroot()
        self.linkAttributes = ['name']

        # Graph
        self.URDF = Namespace("http://knowrob.org/kb/urdf.owl#")
        self.SOMA = Namespace("http://www.ease-crc.org/ont/SOMA.owl#")
        self.robotNS = Namespace("http://example.org/" + self.model_root.attrib['name'] + '/')
        self.robotName = URIRef("http://example.org/" + self.model_root.attrib['name'])
        self.robotKG = Graph().add((self.robotName, RDF.type, self.URDF.Robot))
        self.robotKG.add((self.robotName, self.URDF.hasURDFName, Literal(self.model_root.attrib['name'])))
        # First find all the links and create them in the knowledgeBase
        self.find_links()
        self.find_joints()
        
        print(self.robotKG.serialize(format='ttl'))


    def find_links(self):
        '''
        Looks through all the links and add them to the KG
        So far it only looks at the name of the link and the mass value if specified
        '''
        for link in self.model_root.findall(".//link"):
            # Add the link with it's name to the Knowledge Graph
            self.robotKG.add((self.robotNS[link.attrib['name']], RDF.type, self.URDF.Link))
            self.robotKG.add((self.robotName, self.URDF.hasLink, self.robotNS[link.attrib['name']]))
            self.robotKG.add((self.robotNS[link.attrib['name']], self.URDF.hasURDFName, Literal(link.attrib['name'])))
            # Check if the mass of the link is described
            if link.find('inertial'):
                massValue = link.find('inertial').find('mass').get('value')
                self.robotKG.add((self.robotNS[link.attrib['name']], self.SOMA.hasMassValue, Literal(massValue, datatype=XSD.double)))

    def find_joints(self):
        '''
        Looks through all the joints and add them to the KG
        So far it only looks at the name of the link and the mass value if specified
        '''
        for joint in self.model_root.findall(".//joint"):
            # Add the joint with it's name to the Knowledge Graph
            print(joint.attrib['type'])
            self.robotKG.add((self.robotNS[joint.attrib['name']], RDF.type, self.URDF[joint.attrib['type'].capitalize() + 'Joint']))
            self.robotKG.add((self.robotNS[joint.attrib['name']], self.URDF.hasURDFName, Literal(joint.attrib['name'])))

robot = robot_graph('test/test.urdf')
