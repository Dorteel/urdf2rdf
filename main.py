import xml.etree.ElementTree as ET
from rdflib import Graph, Literal, RDF, URIRef, Namespace, XSD
from rdflib.namespace import SOSA
from io import StringIO


class robot_graph():
    def __init__(self, model_path) -> None:
        # URDF model related variables
        self.model_path = model_path
        self.model = ET.parse(model_path)
        self.model_root = self.model.getroot()
        assert self.model_root.tag == 'robot', "Root is not robot! Check URDF file!"
        #self.linkAttributes = ['name']
        # Deal with arguments
        #print(self.model_root.data)
        self.namespaces = self.get_namespaces()
        # Graph
        self.KnowRob = Namespace("http://knowrob.org/kb/knowrob.owl#")
        self.URDF = Namespace("http://knowrob.org/kb/urdf.owl#")
        self.SOMA = Namespace("http://www.ease-crc.org/ont/SOMA.owl#")
        self.robotNS = Namespace("http://example.org/" + self.model_root.attrib['name'] + '/')
        self.robotName = URIRef("http://example.org/" + self.model_root.attrib['name'])
        self.robotKG = Graph().add((self.robotName, RDF.type, self.URDF.Robot))
        self.robotKG = Graph().add((self.robotName, RDF.type, SOSA.Platform))
        self.robotKG.add((self.robotName, self.URDF.hasURDFName, Literal(self.model_root.attrib['name'])))
        # First find all the links and create them in the knowledgeBase
        self.find_links()
        self.find_joints()
        self.find_sensors()
        #print(self.robotKG.serialize(format='ttl'))


    def get_namespaces(self):
        f = open(self.model_path, "r")
        xml_data = f.read() 
        my_namespaces = dict([node for _, node in ET.iterparse(StringIO(xml_data), events=['start-ns'])])
        return my_namespaces

    
    def find_links(self):
        '''
        Looks through all the links and add them to the KG
         - name
         - mass
         - geometry (box, cylinder, sphere or mesh)
         http://wiki.ros.org/urdf/XML/link
        '''
        for link in self.model_root.findall(".//link"):
            # Add the link with it's name to the Knowledge Graph
            linkNode = self.robotNS[link.attrib['name']]
            self.robotKG.add((linkNode, RDF.type, self.URDF.Link))
            self.robotKG.add((self.robotName, self.URDF.hasLink, linkNode))
            self.robotKG.add((linkNode, self.URDF.hasURDFName, Literal(link.attrib['name'])))
            
            # Check if the mass of the link is described
            if link.find('inertial'):
                massValue = link.find('inertial').find('mass').get('value')
                self.robotKG.add((linkNode, self.SOMA.hasMassValue, Literal(massValue, datatype=XSD.double)))
            
            # Add the shape of the objects and it's properties
            if link.find('.//collision/geometry'):
                shape = list(link.find('collision').find('geometry'))
                assert len(shape) == 1, 'Multiple shapes described for single link {}'.format(link.attrib['name'])
                shapeType = shape[0].tag.capitalize() + 'Shape'
                self.robotKG.add((linkNode, self.SOMA.hasCollisionShape, self.SOMA[shapeType]))
                if shapeType == 'BoxShape':
                    size = [float(x) for x in shape[0].attrib['size'].split(' ')]
                    self.robotKG.add((linkNode, self.SOMA.hasLength, Literal(size[0], datatype=XSD.float)))
                    self.robotKG.add((linkNode, self.SOMA.hasWidth, Literal(size[1], datatype=XSD.float)))
                    self.robotKG.add((linkNode, self.SOMA.hasDepth, Literal(size[2], datatype=XSD.float)))
                elif shapeType == 'CylinderShape':
                    self.robotKG.add((linkNode, self.SOMA.hasRadius, Literal(float(shape[0].attrib['radius']), datatype=XSD.double)))
                    self.robotKG.add((linkNode, self.SOMA.hasLength, Literal(float(shape[0].attrib['length']), datatype=XSD.double)))
                elif shapeType == 'SphereShape':
                    self.robotKG.add((linkNode, self.SOMA.hasRadius, Literal(float(shape[0].attrib['radius']), datatype=XSD.double)))
                else:
                    self.robotKG.add((linkNode, self.SOMA.hasFilePath, Literal(shape[0].attrib['filename'])))


    def find_joints(self):
        '''
        Looks through all the joints and add them to the KG
        So far it only looks at the name of the joint and the mass value if specified
        '''

        # Transmission joints are treated separately
        for actuator in self.model_root.findall("./transmission/actuator"):
            actNode = self.robotNS[actuator.attrib['name']] # Create a node
            self.robotKG.add((actNode, RDF.type, SOSA.Actuator))    # Add as actuator
            self.robotKG.add((self.robotName, SOSA.hosts, actNode)) # Add as part of the robot

        for joint in self.model_root.findall("./joint"):
            # Add the joint with it's name to the Knowledge Graph
            #print(joint.attrib['type'])
            jointNode = self.robotNS[joint.attrib['name']]
            self.robotKG.add((self.robotName, self.URDF.hasJoint, jointNode))
            self.robotKG.add((jointNode, RDF.type, self.URDF[joint.attrib['type'].capitalize() + 'Joint']))
            self.robotKG.add((jointNode, self.URDF.hasURDFName, Literal(joint.attrib['name'])))
            if joint.attrib['type'] in ['revolute', 'prismatic']:
                axis = joint.find('axis').attrib['xyz']
                self.robotKG.add((jointNode, self.URDF.hasAxisVector, Literal(axis))) #TODO: Change to SOMA.array_double
            parent = self.robotNS[joint.find('parent').attrib['link']]
            child = self.robotNS[joint.find('child').attrib['link']]
            self.robotKG.add((jointNode, self.URDF.hasParentLink, parent))
            self.robotKG.add((jointNode, self.URDF.hasChildLink, child))
            
            #print(joint)


    def find_sensors(self):
        '''
        Adds the sensors and their properties to the graph
        http://sdformat.org/spec?ver=1.5&elem=sensor
        Considered sensors: http://wiki.ros.org/urdf/XML/sensor/proposals
        Uses sosa:Sensor
        '''
        for sensor in self.model_root.findall(".//sensor"):
            sensNode = self.robotNS[sensor.attrib['name']] # Create a node
            self.robotKG.add((sensNode, RDF.type, SOSA.Sensor))    # Add as sensor
            self.robotKG.add((self.robotName, SOSA.hosts, sensNode)) # Add as part of the robot
            self.robotKG.add((sensNode, RDF.type, self.KnowRob.SensorDevice)) 
            # Add the properties of the sensor
            type = sensor.attrib['type']
            if type == 'ray':
                ray = sensor.find('ray')
                print(ray.getchildren())
            elif type == 'camera':
                pass
            elif type == 'imu':
                pass

if __name__ == "__main__":
    robots = ['test/model.urdf', 'test/turtlebot3_burger.urdf', 'test/baxter.urdf']
    for robot in robots:
        print('\n{}\n{}\n{}\n'.format('*'*len(robot), robot, '*'*len(robot)))
        robot_graph(robot)