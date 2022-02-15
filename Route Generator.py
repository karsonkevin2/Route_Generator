"""
Model exported as python.
Name : Route Generator
Group : 
With QGIS : 32202
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterPoint
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterDefinition
import processing


class RouteGenerator(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterNumber('AOIRadiusm', 'AOI Radius (m)', type=QgsProcessingParameterNumber.Double, defaultValue=5000))
        param = QgsProcessingParameterNumber('JunctionTolerance', 'Junction Tolerance (m)', type=QgsProcessingParameterNumber.Double, minValue=-1.79769e+308, maxValue=1.79769e+308, defaultValue=1)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterNumber('PointDensitypointm2', 'Point Density (points/m^2)', type=QgsProcessingParameterNumber.Double, minValue=-1.79769e+308, maxValue=1.79769e+308, defaultValue=1e-05)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        self.addParameter(QgsProcessingParameterVectorLayer('RoutingNetwork', 'Routing Network (m)', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterEnum('RoutingType', 'Routing Type', options=['Shortest','Weighted'], allowMultiple=False, usesStaticStrings=False, defaultValue=None))
        self.addParameter(QgsProcessingParameterPoint('StartEnd', 'Start/End', defaultValue='0.000000,0.000000'))
        self.addParameter(QgsProcessingParameterField('Weights', 'Weights', type=QgsProcessingParameterField.Numeric, parentLayerParameterName='RoutingNetwork', allowMultiple=False, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Aoi', 'AOI', type=QgsProcessing.TypeVectorPolygon, createByDefault=True, supportsAppend=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('OptimalRoutes', 'Optimal Routes', type=QgsProcessing.TypeVectorLine, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Destinations', 'Destinations', type=QgsProcessing.TypeVectorPoint, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(4, model_feedback)
        results = {}
        outputs = {}

        # Convert to Layer
        alg_params = {
            'INPUT': parameters['StartEnd'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ConvertToLayer'] = processing.run('native:pointtolayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Create AOI
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': parameters['AOIRadiusm'],
            'END_CAP_STYLE': 0,  # Round
            'INPUT': outputs['ConvertToLayer']['OUTPUT'],
            'JOIN_STYLE': 0,  # Round
            'MITER_LIMIT': 2,
            'SEGMENTS': 100,
            'OUTPUT': parameters['Aoi']
        }
        outputs['CreateAoi'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Aoi'] = outputs['CreateAoi']['OUTPUT']

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Seed Destinations
        alg_params = {
            'INPUT': outputs['CreateAoi']['OUTPUT'],
            'MIN_DISTANCE': None,
            'STRATEGY': 1,  # Points density
            'VALUE': parameters['PointDensitypointm2'],
            'OUTPUT': parameters['Destinations']
        }
        outputs['SeedDestinations'] = processing.run('qgis:randompointsinsidepolygons', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Destinations'] = outputs['SeedDestinations']['OUTPUT']

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Generate Routes
        alg_params = {
            'DEFAULT_DIRECTION': 2,  # Both directions
            'DEFAULT_SPEED': 50,
            'DIRECTION_FIELD': '',
            'END_POINTS': outputs['SeedDestinations']['OUTPUT'],
            'INPUT': parameters['RoutingNetwork'],
            'SPEED_FIELD': parameters['Weights'],
            'START_POINT': parameters['StartEnd'],
            'STRATEGY': parameters['RoutingType'],
            'TOLERANCE': parameters['JunctionTolerance'],
            'VALUE_BACKWARD': '',
            'VALUE_BOTH': '',
            'VALUE_FORWARD': '',
            'OUTPUT': parameters['OptimalRoutes']
        }
        outputs['GenerateRoutes'] = processing.run('native:shortestpathpointtolayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['OptimalRoutes'] = outputs['GenerateRoutes']['OUTPUT']
        return results

    def name(self):
        return 'Route Generator'

    def displayName(self):
        return 'Route Generator'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return RouteGenerator()
