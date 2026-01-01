import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'dart:html' as html; // Para som no web

void main() {
  runApp(const MotoboyApp());
}

class MotoboyApp extends StatelessWidget {
  const MotoboyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'App Motoboy',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: const InitialScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class InitialScreen extends StatelessWidget {
  const InitialScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final isMobile = size.width < 600;

    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: EdgeInsets.all(isMobile ? 20 : 40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.motorcycle, size: isMobile ? 80 : 100, color: Colors.blue),
              SizedBox(height: isMobile ? 20 : 30),
              Text("App Motoboy", style: TextStyle(fontSize: isMobile ? 28 : 32, fontWeight: FontWeight.bold)),
              SizedBox(height: isMobile ? 40 : 60),
              SizedBox(
                width: isMobile ? double.infinity : 400,
                child: ElevatedButton(
                  onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const LoginScreen())),
                  child: const Text("Entrar com código", style: TextStyle(fontSize: 18)),
                ),
              ),
              SizedBox(height: isMobile ? 10 : 20),
              SizedBox(
                width: isMobile ? double.infinity : 400,
                child: ElevatedButton(
                  onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const RegisterScreen())),
                  child: const Text("Criar conta nova", style: TextStyle(fontSize: 18)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _codigoController = TextEditingController();
  final _nomeController = TextEditingController();
  final _sobrenomeController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmController = TextEditingController();
  String? _errorMessage;
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final isMobile = size.width < 600;

    return Scaffold(
      appBar: AppBar(title: const Text("Criar Conta")),
      body: Center(
        child: SingleChildScrollView(
          padding: EdgeInsets.all(isMobile ? 20 : 40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.person_add, size: isMobile ? 80 : 100, color: Colors.blue),
              SizedBox(height: isMobile ? 20 : 30),
              Text("Cadastro Motoboy", style: TextStyle(fontSize: isMobile ? 24 : 28, fontWeight: FontWeight.bold)),
              SizedBox(height: isMobile ? 20 : 30),
              SizedBox(
                width: isMobile ? double.infinity : 400,
                child: TextField(
                  controller: _codigoController,
                  decoration: const InputDecoration(labelText: "Código do restaurante", border: OutlineInputBorder()),
                ),
              ),
              SizedBox(height: isMobile ? 10 : 20),
              SizedBox(
                width: isMobile ? double.infinity : 400,
                child: TextField(
                  controller: _nomeController,
                  decoration: const InputDecoration(labelText: "Nome", border: OutlineInputBorder()),
                ),
              ),
              SizedBox(height: isMobile ? 10 : 20),
              SizedBox(
                width: isMobile ? double.infinity : 400,
                child: TextField(
                  controller: _sobrenomeController,
                  decoration: const InputDecoration(labelText: "Sobrenome", border: OutlineInputBorder()),
                ),
              ),
              SizedBox(height: isMobile ? 10 : 20),
              SizedBox(
                width: isMobile ? double.infinity : 400,
                child: TextField(
                  controller: _usernameController,
                  decoration: const InputDecoration(labelText: "Username (único)", border: OutlineInputBorder()),
                ),
              ),
              SizedBox(height: isMobile ? 10 : 20),
              SizedBox(
                width: isMobile ? double.infinity : 400,
                child: TextField(
                  controller: _passwordController,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: "Senha", border: OutlineInputBorder()),
                ),
              ),
              SizedBox(height: isMobile ? 10 : 20),
              SizedBox(
                width: isMobile ? double.infinity : 400,
                child: TextField(
                  controller: _confirmController,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: "Confirmar senha", border: OutlineInputBorder()),
                ),
              ),
              if (_errorMessage != null)
                Padding(
                  padding: EdgeInsets.only(top: isMobile ? 10 : 20),
                  child: Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
                ),
              SizedBox(height: isMobile ? 20 : 30),
              SizedBox(
                width: isMobile ? double.infinity : 400,
                child: ElevatedButton(
                  onPressed: _loading ? null : () async {
                    if (_passwordController.text != _confirmController.text) {
                      setState(() => _errorMessage = "Senhas não coincidem");
                      return;
                    }
                    setState(() {
                      _loading = true;
                      _errorMessage = null;
                    });
                    try {
                      final response = await http.post(
                        Uri.parse("http://192.168.0.193:8000/motoboys/register/"),
                        headers: {"Content-Type": "application/json"},
                        body: jsonEncode({
                          "codigo_acesso": _codigoController.text.trim(),
                          "nome": "${_nomeController.text} ${_sobrenomeController.text}",
                          "username": _usernameController.text.trim(),
                          "password": _passwordController.text,
                        }),
                      );
                      if (response.statusCode == 200) {
                        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Cadastro realizado! Use o código para entrar")));
                        Navigator.pop(context);
                      } else {
                        setState(() => _errorMessage = "Erro no cadastro");
                      }
                    } catch (e) {
                      setState(() => _errorMessage = "Erro de conexão");
                    } finally {
                      setState(() => _loading = false);
                    }
                  },
                  child: _loading ? const CircularProgressIndicator(color: Colors.white) : const Text("Cadastrar", style: TextStyle(fontSize: 18)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _codigoController = TextEditingController();
  String? _errorMessage;
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final isMobile = size.width < 600;

    return Scaffold(
      appBar: AppBar(title: const Text("Login Motoboy")),
      body: Center(
        child: SingleChildScrollView(
          padding: EdgeInsets.all(isMobile ? 20 : 40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.motorcycle, size: isMobile ? 80 : 100, color: Colors.blue),
              SizedBox(height: isMobile ? 20 : 30),
              Text("Entrar com código", style: TextStyle(fontSize: isMobile ? 24 : 28, fontWeight: FontWeight.bold)),
              SizedBox(height: isMobile ? 20 : 30),
              SizedBox(
                width: isMobile ? double.infinity : 400,
                child: TextField(
                  controller: _codigoController,
                  decoration: const InputDecoration(
                    labelText: "Código de Acesso",
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              if (_errorMessage != null)
                Padding(
                  padding: EdgeInsets.only(top: isMobile ? 10 : 20),
                  child: Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
                ),
              SizedBox(height: isMobile ? 20 : 30),
              SizedBox(
                width: isMobile ? double.infinity : 400,
                child: ElevatedButton(
                  onPressed: _loading
                      ? null
                      : () async {
                          String codigo = _codigoController.text.trim();
                          if (codigo.isEmpty) {
                            setState(() => _errorMessage = "Digite o código");
                            return;
                          }

                          setState(() {
                            _loading = true;
                            _errorMessage = null;
                          });

                          try {
                            final response = await http.post(
                              Uri.parse("http://192.168.0.193:8000/motoboys/login/"),
                              headers: {"Content-Type": "application/json"},
                              body: jsonEncode({"codigo_acesso": codigo}),
                            );

                            if (response.statusCode == 200) {
                              final data = jsonDecode(response.body);
                              Navigator.pushReplacement(
                                context,
                                MaterialPageRoute(
                                  builder: (context) => HomeScreen(
                                    motoboyId: data["motoboy_id"].toString(),
                                    nomeMotoboy: data["nome"],
                                  ),
                                ),
                              );
                            } else {
                              setState(() => _errorMessage = "Código inválido");
                            }
                          } catch (e) {
                            setState(() => _errorMessage = "Erro de conexão");
                          } finally {
                            setState(() => _loading = false);
                          }
                        },
                  child: _loading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text("Entrar", style: TextStyle(fontSize: 18)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class HomeScreen extends StatefulWidget {
  final String motoboyId;
  final String nomeMotoboy;

  const HomeScreen({
    super.key,
    required this.motoboyId,
    required this.nomeMotoboy,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Position? _currentPosition;
  Timer? _gpsTimer;
  Timer? _pollTimer;
  List<dynamic> _pedidosAnteriores = [];

  @override
  void initState() {
    super.initState();
    _startLocationUpdates();
    _startPollingPedidos();
  }

  Future<void> _startLocationUpdates() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Ative o GPS")));
      return;
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    _gpsTimer = Timer.periodic(const Duration(seconds: 30), (timer) async {
      try {
        Position position = await Geolocator.getCurrentPosition(desiredAccuracy: LocationAccuracy.high);
        setState(() {
          _currentPosition = position;
        });

        await http.post(
          Uri.parse("http://192.168.0.193:8000/motoboys/gps/"),
          headers: {"Content-Type": "application/json"},
          body: jsonEncode({
            "motoboy_id": int.parse(widget.motoboyId),
            "latitude": position.latitude,
            "longitude": position.longitude,
          }),
        );
      } catch (e) {
        // Silencioso
      }
    });
  }

  void _startPollingPedidos() {
    _pollTimer = Timer.periodic(const Duration(seconds: 5), (timer) async {
      try {
        final response = await http.get(Uri.parse("http://192.168.0.193:8000/pedidos/motoboy/${widget.motoboyId}"));
        if (response.statusCode == 200) {
          final pedidos = jsonDecode(response.body);
          if (pedidos.length > _pedidosAnteriores.length) {
            // Novo pedido
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text("Novo pedido recebido!"),
                backgroundColor: Colors.green,
                duration: Duration(seconds: 10),
              ),
            );
            // Som no navegador
            html.AudioElement('https://www.soundjay.com/buttons/beep-07.mp3')..play();
          }
          _pedidosAnteriores = pedidos;
        }
      } catch (e) {
        // Silencioso
      }
    });
  }

  @override
  void dispose() {
    _gpsTimer?.cancel();
    _pollTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final isMobile = size.width < 600;

    return Scaffold(
      appBar: AppBar(title: Text("Olá, ${widget.nomeMotoboy}")),
      body: Center(
        child: SingleChildScrollView(
          padding: EdgeInsets.all(isMobile ? 20 : 40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.online_prediction, size: isMobile ? 100 : 120, color: Colors.green),
              Text("Online", style: TextStyle(fontSize: isMobile ? 26 : 32, fontWeight: FontWeight.bold, color: Colors.green)),
              SizedBox(height: isMobile ? 20 : 30),
              if (_currentPosition != null)
                Text(
                  "GPS enviado:\nLat: ${_currentPosition!.latitude.toStringAsFixed(6)}\nLng: ${_currentPosition!.longitude.toStringAsFixed(6)}",
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: isMobile ? 16 : 18),
                )
              else
                const Text("Obtendo posição GPS...", style: TextStyle(fontSize: 18)),
              SizedBox(height: isMobile ? 30 : 40),
              Text("Aguardando pedidos...", style: TextStyle(fontSize: isMobile ? 20 : 24)),
            ],
          ),
        ),
      ),
    );
  }
}