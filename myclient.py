from apikey.client import Client


class MyClient(Client):
    """inherited from OnShape public apikey python client, 
    with additional method for parsing cad.
    """
    def eval_boundingBox(self, did, wid, eid):
        '''
        Get bounding box of all solid bodies for specified document / workspace / part studio.

        Args:
            - did (str): Document ID
            - wid (str): Workspace ID
            - eid (str): Element ID

        Returns:
            - dict: {'maxCorner': [], 'minCorner': []}
        '''
        body = {
            "script":
                "function(context is Context, queries) { " +
                "   var q_body = qBodyType(qEverything(EntityType.BODY), BodyType.SOLID);"
                "   var bbox = evBox3d(context, {'topology': q_body});"
                "   return bbox;"
                "}",
            "queries": []
        }
        response = self._api.request('post', '/api/partstudios/d/' + did + '/w/' + wid + '/e/' + eid + '/featurescript', body=body)
        bbox_values = response.json()['result']['message']['value']
        result = {}
        for item in bbox_values:
            k = item['message']['key']['message']['value']
            point_values = item['message']['value']['message']['value']
            v = [x['message']['value'] for x in point_values]
            result.update({k: v})
        return result

    def get_entity_by_id(self, did, wid, eid, geo_id, entity_type):
        """get the parameters of geometry entity for specified entity id and type

        Args:
            - did (str): Document ID
            - wid (str): Workspace ID
            - eid (str): Element ID
            - geo_id (str): geometry entity ID
            - entity_type (str): 'VERTEX', 'EDGE' or 'FACE'

        Returns:
            - requests.Response: OnShape response data
        """
        func_dict = {"VERTEX": ("evVertexPoint", "vertex"),
                     "EDGE": ("evCurveDefinition", "edge"),
                     "FACE": ("evSurfaceDefinition", "face")}
        body = {
            "script":
                "function(context is Context, queries) { " +
                "   var res_list = [];"
                "   var q_arr = evaluateQuery(context, queries.id);"
                "   for (var i = 0; i < size(q_arr); i+= 1){"
                "       var res = %s(context, {\"%s\": q_arr[i]});" % (func_dict[entity_type][0], func_dict[entity_type][1]) +
                "       res_list = append(res_list, res);"
                "   }"
                "   return res_list;"
                "}",
            "queries": [{ "key" : "id", "value" : geo_id }]
        }
        res = self._api.request('post', '/api/partstudios/d/' + did + '/w/' + wid + '/e/' + eid + '/featurescript', body=body)

        return res

    def eval_sketch_topology_by_adjacency(self, did, wid, eid, feat_id):
        """parse the hierarchical parametric geometry&topology (face -> edges -> vertex)
        from a specified sketch feature ID.

        Args:
            - did (str): Document ID
            - wid (str): Workspace ID
            - eid (str): Element ID
            - feat_id (str): Feature ID of a sketch 

        Returns:
            - dict: a hierarchical parametric representation
        """
        body = {
            "script":
                "function(context is Context, queries) { "
                "   var topo = {};"
                "   topo.faces = [];"
                "   topo.edges = [];"
                "   topo.vertices = [];"
                "   var all_edge_ids = [];"
                "   var all_vertex_ids = [];"
                "                           "
                "   var q_face = qSketchRegion(makeId(\"%s\"));" % feat_id +
                # "   var q_face = qCreatedBy(makeId(\"%s\"), EntityType.FACE);" % feat_id +
                "   var face_arr = evaluateQuery(context, q_face);"
                "   for (var i = 0; i < size(face_arr); i += 1) {"
                "       var face_topo = {};"
                "       const face_id = transientQueriesToStrings(face_arr[i]);"
                "       face_topo.id = face_id;"
                "       face_topo.edges = [];"
                "       face_topo.param = evSurfaceDefinition(context, {face: face_arr[i]});"
                "                            "
                # "       var q_edge = qLoopEdges(q_face);"
                "       var q_edge = qAdjacent(face_arr[i], AdjacencyType.EDGE, EntityType.EDGE);"
                "       var edge_arr = evaluateQuery(context, q_edge);"
                "       for (var j = 0; j < size(edge_arr); j += 1) {"
                "           var edge_topo = {};"
                "           const edge_id = transientQueriesToStrings(edge_arr[j]);"
                "           edge_topo.id = edge_id;"
                "           edge_topo.vertices = [];"
                "           edge_topo.param = evCurveDefinition(context, {edge: edge_arr[j]});" # 
                "           edge_topo.param.midpoint = evEdgeTangentLine(context, {\"edge\": edge_arr[j], \"parameter\": 0.5 }).origin;" #Makes eval_curve_midpoint obsolete
                "           face_topo.edges = append(face_topo.edges, edge_id);"
                "                                  "
                "           var q_vertex = qAdjacent(edge_arr[j], AdjacencyType.VERTEX, EntityType.VERTEX);"
                "           var vertex_arr = evaluateQuery(context, q_vertex);"
                "           for (var k = 0; k < size(vertex_arr); k += 1) {"
                "               var vertex_topo = {};"
                "               const vertex_id = transientQueriesToStrings(vertex_arr[k]);"
                "               vertex_topo.id = vertex_id;"
                "               vertex_topo.param = evVertexPoint(context, {vertex: vertex_arr[k]});"
                "               edge_topo.vertices = append(edge_topo.vertices, vertex_id);"
                "               if (isIn(vertex_id, all_vertex_ids)){continue;}"
                "               all_vertex_ids = append(all_vertex_ids, vertex_id);"
                "               topo.vertices = append(topo.vertices, vertex_topo);"
                "           }"
                "           if (isIn(edge_id, all_edge_ids)){continue;}"
                "           all_edge_ids = append(all_edge_ids, edge_id);"
                "           topo.edges = append(topo.edges, edge_topo);"
                "       }"
                "       topo.faces = append(topo.faces, face_topo);"
                "   }"
                "   return topo;"
                "}",
            "queries": []
        }
        res = self._api.request('post', '/api/partstudios/d/' + did + '/w/' + wid + '/e/' + eid + '/featurescript', body=body)

        res_msg = res.json()['result']['message']['value']
        topo = {}
        for item in res_msg:
            item_msg = item['message']
            k_str = item_msg['key']['message']['value'].encode('utf-8')  # faces, edges
            v_item = item_msg['value']['message']['value']
            outer_list = []
            for item_x in v_item:
                v_item_x = item_x['message']['value']
                geo_dict = {}
                for item_y in v_item_x:
                    k = item_y['message']['key']['message']['value'].encode('utf-8')  # id, edges/vertices
                    v_msg = item_y['message']['value']
                    if k == 'param':
                        if k_str == 'faces':
                            v = MyClient.parse_face_msg(v_msg)[0]
                        elif k_str == 'edges':
                            v = MyClient.parse_edge_msg(v_msg)[0]
                        elif k_str == 'vertices':
                            v = MyClient.parse_vertex_msg(v_msg)[0]
                        else:
                            raise ValueError
                    elif isinstance(v_msg['message']['value'], list):
                        v = [a['message']['value'].encode('utf-8') for a in v_msg['message']['value']]
                    else:
                        v = v_msg['message']['value'].encode('utf-8')
                    geo_dict.update({k: v})
                outer_list.append(geo_dict)
            topo.update({k_str: outer_list})
        return topo

    @staticmethod
    def parse_vertex_msg(response):
        """parse vertex parameters from OnShape response data"""
        # data = response.json()['result']['message']['value']
        data = [response] if not isinstance(response, list) else response
        vertices = []
        for item in data:
            xyz_msg = item['message']['value']
            xyz_type = item['message']['typeTag'].encode('utf-8')
            p = []
            for msg in xyz_msg:
                p.append(round(msg['message']['value'], 8))
            unit = xyz_msg[0]['message']['unitToPower'][0]
            unit_exp = (unit['key'].encode('utf-8'), unit['value'])
            vertices.append({xyz_type: tuple(p), 'unit': unit_exp})
        return vertices

    @staticmethod
    def parse_coord_msg(response):
        """parse coordSystem parameters from OnShape response data"""
        coord_param = {}
        for item in response:
            k_msg = item['message']['key']
            k = k_msg['message']['value'].encode('utf-8')
            v_msg = item['message']['value']
            v = [round(x['message']['value'], 8) for x in v_msg['message']['value']]
            coord_param.update({k: v})
        return coord_param

    @staticmethod
    def parse_edge_msg(response):
        """parse edge parameters from OnShape response data"""
        # data = response.json()['result']['message']['value']
        data = [response] if not isinstance(response, list) else response
        edges = []
        for item in data:
            edge_msg = item['message']['value']
            edge_type = item['message']['typeTag'].encode('utf-8')
            edge_param = {'type': edge_type}
            for msg in edge_msg:
                k = msg['message']['key']['message']['value'].encode('utf-8')
                v_item = msg['message']['value']['message']['value']
                if k == 'coordSystem':
                    v = MyClient.parse_coord_msg(v_item)
                elif isinstance(v_item, list):
                    v = [round(x['message']['value'], 8) for x in v_item]
                else:
                    if isinstance(v_item, float):
                        v = round(v_item, 8)
                    else:
                        v = v_item.encode('utf-8')
                edge_param.update({k: v})
            edges.append(edge_param)
        return edges

    @staticmethod
    def parse_face_msg(response):
        """parse face parameters from OnShape response data"""
        # data = response.json()['result']['message']['value']
        data = [response] if not isinstance(response, list) else response
        faces = []
        for item in data:
            face_msg = item['message']['value']
            face_type = item['message']['typeTag'].encode('utf-8')
            face_param = {'type': face_type}
            for msg in face_msg:
                k = msg['message']['key']['message']['value'].encode('utf-8')
                v_item = msg['message']['value']['message']['value']
                if k == 'coordSystem':
                    v = MyClient.parse_coord_msg(v_item)
                elif isinstance(v_item, list):
                    v = [round(x['message']['value'], 8) for x in v_item]
                else:
                    if isinstance(v_item, float):
                        v = round(v_item, 8)
                    else:
                        v = v_item.encode('utf-8')
                face_param.update({k: v})
            faces.append(face_param)
        return faces