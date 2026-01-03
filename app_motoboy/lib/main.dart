import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:location/location.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: "assets/.env");
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Super Restaurante - Motoboy',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(primarySwatch: Colors.orange, useMaterial3: true),
      home: const MotoboyHomePage(),
    );
  }
}

class MotoboyHomePage extends StatefulWidget {
  const MotoboyHomePage({super.key});

  @override
  State<MotoboyHomePage> createState() => _MotoboyHomePageState();
}

class _MotoboyHomePageState extends State<MotoboyHomePage> {
  final MapController _mapController = MapController();
  Location location = Location();
  StreamSubscription<LocationData>? _locationSubscription;

  LatLng? currentPosition;  // Posição atual do motoboy
  double currentHeading = 0.0;  // Direção (graus)

  List<Map<String, dynamic>> pedidos = [];

  @override
  void initState() {
    super.initState();
    _initLocationTracking();
    _mockPedidosParaTeste();
  }

  Future<void> _initLocationTracking() async {
    bool serviceEnabled = await location.serviceEnabled();
    if (!serviceEnabled) {
      serviceEnabled = await location.requestService();
      if (!serviceEnabled) return;
    }

    PermissionStatus permission = await location.hasPermission();
    if (permission == PermissionStatus.denied) {
      permission = await location.requestPermission();
      if (permission != PermissionStatus.granted) return;
    }

    location.changeSettings(accuracy: LocationAccuracy.high, interval: 3000);

    _locationSubscription = location.onLocationChanged.listen((LocationData data) {
      if (data.latitude != null && data.longitude != null) {
        setState(() {
          currentPosition = LatLng(data.latitude!, data.longitude!);
          if (data.heading != null) currentHeading = data.heading!;
        });

        // Centraliza automaticamente na primeira localização e depois segue suave
        _mapController.move(currentPosition!, 16.0);
      }
    });
  }

  void _recenterMap() {
    if (currentPosition != null) {
      _mapController.move(currentPosition!, 16.0);
    }
  }

  void _mockPedidosParaTeste() {
    setState(() {
      pedidos = [
        {"id": 1, "endereco": "Rua A, 123", "sequencia": 1, "cliente": "João"},
        {"id": 2, "endereco": "Av. B, 456", "sequencia": 2, "cliente": "Maria"},
      ];
    });
  }

  @override
  Widget build(BuildContext context) {
    final mapboxToken = dotenv.env['MAPBOX_TOKEN'] ?? '';

    return Scaffold(
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: const MapOptions(
              initialCenter: LatLng(-23.5505, -46.6333), // Fallback SP
              initialZoom: 15.0,
            ),
            children: [
              TileLayer(
                urlTemplate:
                    'https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}',
                additionalOptions: {
                  'accessToken': mapboxToken,
                  'id': 'mapbox/streets-v12',
                },
              ),
              if (currentPosition != null)
                MarkerLayer(
                  markers: [
                    Marker(
                      point: currentPosition!,
                      width: 40,
                      height: 40,
                      child: RotationTransition(
                        turns: AlwaysStoppedAnimation(currentHeading / 360),
                        child: const Icon(
                          Icons.directions_bike,
                          color: Colors.blue,
                          size: 40,
                        ),
                      ),
                    ),
                  ],
                ),
            ],
          ),
          if (pedidos.isNotEmpty)
            DraggableScrollableSheet(
              initialChildSize: 0.4,
              minChildSize: 0.2,
              maxChildSize: 0.9,
              builder: (_, controller) {
                return Container(
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                  ),
                  child: Column(
                    children: [
                      const Padding(
                        padding: EdgeInsets.all(16),
                        child: Text(
                          "Pedidos Atribuidos",
                          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                        ),
                      ),
                      Expanded(
                        child: ListView.builder(
                          controller: controller,
                          itemCount: pedidos.length,
                          itemBuilder: (_, i) {
                            final p = pedidos[i];
                            return ListTile(
                              title: Text("Entrega ${p['sequencia']}: ${p['cliente']}"),
                              subtitle: Text(p['endereco']),
                              trailing: i == 0
                                  ? ElevatedButton(
                                      onPressed: () {}, child: const Text("Iniciar Rota"))
                                  : null,
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _recenterMap,
        child: const Icon(Icons.my_location),
      ),
    );
  }

  @override
  void dispose() {
    _locationSubscription?.cancel();
    super.dispose();
  }
}