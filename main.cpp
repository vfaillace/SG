#define NOMINMAX
#include <imgui.h>
#include <imgui_impl_glfw.h>
#include <imgui_impl_opengl3.h>
#include <GLFW/glfw3.h>
#ifndef IMPLOT_H
#define IMPLOT_H
#include <implot.h>
#endif
#include <iostream>
#include <vector>
#include <string>
#include <thread>
#include <mutex>
#include <queue>
#include <Python.h>
#include <cstdlib>
#include <WinSock2.h>
#include <WS2tcpip.h>
#include <limits>
#ifndef IMPLOT_INTERNAL_H
#define IMPLOT_INTERNAL_H
#include <implot_internal.h>
#endif
#include <nlohmann/json.hpp>
#include <unordered_map>
#include <algorithm>
#include <unordered_set>
#include <thread>
#include <sqlite3.h>
#include <filesystem>
#include <Windows.h>
#include <commdlg.h>
#include <ctime>
#include <iomanip>
#include <sstream>

#pragma comment(lib, "Ws2_32.lib")
using json = nlohmann::json;
#include <random>

std::vector<std::thread> pythonScriptThreads;
std::atomic<bool> applicationClosing(false);
static float globalScrollX = 0.0f;
static bool isScrolling = false;
static bool scrollFromPlot = false; // To track which plot triggered the scroll

enum class DataSource
{
    SIMULATION,
    WIRESHARK
};

DataSource currentDataSource = DataSource::SIMULATION;
bool wiresharkRunning = false;
std::thread wiresharkThread;

enum class AttackType
{
    NONE,
    DDOS,
    SYN_FLOOD,
    MITM_SCADA
};

struct AttackInfo
{
    bool none;
    bool ddos;
    bool synflood;
    bool mitm;
};

enum class TrafficType
{
    NORMAL,
    DDOS,
    SYN_FLOOD,
    MITM_SCADA
};

TrafficType currentTrafficType = TrafficType::NORMAL;

const char *attackLabels[] = {"None", "DDoS", "SYN Flood", "MITM"};

struct PlotData
{
    // std::map<std::pair<int, int>, std::vector<float>> time;
    std::map<std::pair<int, int>, std::vector<float>> values;
};
struct ModelInfo
{
    std::string name;
    std::string path;
    bool selected;
    SOCKET socket;
    int port;
    ImVec4 color;
    std::vector<PlotData> plotData;
    std::map<AttackType, float> attackAccuracy;
    ModelInfo() : plotData(1) {} // Initialize with one PlotData for predictions
};
std::vector<std::string> metricLabels = {
    "Packets Dropped",
    "Average Queue Size",
    "System Occupancy",
    "Service Rate",
    "Transmission Delay",
    "Round Trip Time (RTT)",
    "Arrival Rate",
    "Attack Type",
    "Packet Size",
    "IAT",
    "Acknowledgement Size",
    "Packet Count (PC)"};

// Update the plotDataArray size initialization
std::vector<PlotData> plotDataArray(metricLabels.size());
std::vector<std::mutex> plotDataMutexes(metricLabels.size());
std::vector<bool> plotVisibility(metricLabels.size(), true);

std::random_device rd;
std::mt19937 gen(rd());
std::uniform_int_distribution<> portDist(12348, 65535); 

std::vector<ModelInfo> availableModels;
std::mutex modelsMutex;
struct pair_hash
{
    template <class T1, class T2>
    std::size_t operator()(const std::pair<T1, T2> &p) const
    {
        auto h1 = std::hash<T1>{}(p.first);
        auto h2 = std::hash<T2>{}(p.second);
        return h1 ^ h2;
    }
};

std::unordered_map<std::pair<int, int>, int, pair_hash> fbTbCombinations;
const int MAX_COMBINATIONS = 10; 
const int MAX_LINES = 10;        
std::queue<std::vector<float>> dataQueue;
std::vector<json> modelStats;
std::mutex queueMutex;
bool simulationRunning = false;
bool simulationEnded = false;
bool includeDOS = true;       // Global variable to control DOS inclusion
int totalSimulationTime = 20; // Default total simulation time in seconds
int dosAttackTime = 10;       // Default DOS attack time in seconds
std::atomic<bool> stopSimulationRequested(false);
std::atomic<bool> receiverRunning(true);
SOCKET predictionSocket = INVALID_SOCKET;
std::atomic<bool> shouldExit(false);
SOCKET listenSocket = INVALID_SOCKET;

ImVec4 colors[] = {
    ImVec4(1.0f, 0.0f, 0.0f, 1.0f), // Red
    ImVec4(0.0f, 1.0f, 0.0f, 1.0f), // Green
    ImVec4(0.0f, 0.0f, 1.0f, 1.0f), // Blue
    ImVec4(1.0f, 1.0f, 0.0f, 1.0f), // Yellow
    ImVec4(1.0f, 0.0f, 1.0f, 1.0f), // Magenta
    ImVec4(0.0f, 1.0f, 1.0f, 1.0f), // Cyan
    ImVec4(1.0f, 0.5f, 0.0f, 1.0f), // Orange
    ImVec4(0.5f, 0.0f, 0.5f, 1.0f), // Purple
    ImVec4(0.0f, 0.5f, 0.5f, 1.0f), // Teal
    ImVec4(0.5f, 0.5f, 0.5f, 1.0f)  // Gray
};

const ImVec4 ATTACK_COLORS[] = {
    ImVec4(0.5f, 0.5f, 0.5f, 1.0f), // Normal traffic (Grey)
    ImVec4(1.0f, 0.0f, 0.0f, 1.0f), // DDoS (Red)
    ImVec4(0.0f, 0.0f, 1.0f, 1.0f), // SYN Flood (Blue)
    ImVec4(1.0f, 0.6f, 0.0f, 1.0f)  // MITM (Orange)
};

// Function to initialize Python

void updateSimulationParameters()
{
    ImGui::InputInt("Total Simulation Time (s)", &totalSimulationTime);

    static int selectedAttackType = 0;
    const char *attackTypes[] = {"None", "DDoS", "SYN Flood", "MITM SCADA"};
    ImGui::Combo("Attack Type", &selectedAttackType, attackTypes, IM_ARRAYSIZE(attackTypes));

    if (selectedAttackType > 0)
    {
        ImGui::InputInt("Attack Duration (s)", &dosAttackTime);
        if (dosAttackTime > totalSimulationTime)
        {
            dosAttackTime = totalSimulationTime;
        }
    }
}

void processPredictionResponse(ModelInfo &model, const json &response, const std::pair<int, int> &connection)
{
    float prediction = response["prediction"].get<float>();
    std::string attackType = response["attack_type"].get<std::string>();
    // std::cout << prediction << std::endl;
    // std::cout << attackType << std::endl;

    // Update plot data
    model.plotData[0].values[connection].push_back(prediction);

    // Limit the size of the plot data
    if (model.plotData[0].values[connection].size() > 1000)
    {
        model.plotData[0].values[connection].erase(
            model.plotData[0].values[connection].begin());
    }
}

std::string openFileDialog(const char *filter = "Python Files\0*.py\0All Files\0*.*\0")
{
    OPENFILENAMEA ofn;
    char szFile[260] = {0};
    ZeroMemory(&ofn, sizeof(ofn));
    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = NULL;
    ofn.lpstrFile = szFile;
    ofn.nMaxFile = sizeof(szFile);
    ofn.lpstrFilter = filter;
    ofn.nFilterIndex = 1;
    ofn.lpstrFileTitle = NULL;
    ofn.nMaxFileTitle = 0;
    ofn.lpstrInitialDir = NULL;
    ofn.Flags = OFN_PATHMUSTEXIST | OFN_FILEMUSTEXIST;

    if (GetOpenFileNameA(&ofn) == TRUE)
    {
        return ofn.lpstrFile;
    }
    return "";
}

bool fileExists(const std::string &path)
{
    return std::filesystem::exists(path);
}


void initAvailableModels()
{
    std::vector<std::string> modelNames = {
        "isolation_forest_model.pkl",
        "decision_tree_model.pkl",
        "kmeans_model.pkl",
        "random_forest_model.pkl"};
    for (size_t i = 0; i < modelNames.size(); ++i)
    {
        ModelInfo model;
        model.name = modelNames[i];
        model.selected = false;
        model.socket = INVALID_SOCKET;
        model.port = portDist(gen);
        model.color = colors[i % MAX_LINES];
        availableModels.push_back(model);
    }
}

void loadModel()
{
    std::string customModelPath = openFileDialog("Pickle Files\0*.pkl\0All Files\0*.*\0");
    if (!customModelPath.empty())
    {
        ModelInfo customModel;
        customModel.name = "Custom: " + std::filesystem::path(customModelPath).filename().string();
        customModel.selected = false;
        customModel.socket = INVALID_SOCKET;
        customModel.port = portDist(gen);
        customModel.color = colors[availableModels.size() % MAX_LINES];
        customModel.path = std::filesystem::absolute(customModelPath).string(); // Store the full absolute path

        std::lock_guard<std::mutex> lock(modelsMutex);
        availableModels.push_back(customModel);
    }
}

std::string getCurrentTimestamp()
{
    auto now = std::chrono::system_clock::now();
    auto in_time_t = std::chrono::system_clock::to_time_t(now);

    std::stringstream ss;
    ss << std::put_time(std::localtime(&in_time_t), "%Y%m%d_%H%M%S");
    return ss.str();
}

void trainModel(const std::string &csvPath)
{
    std::string scriptPath = openFileDialog("Python Files\0*.py\0All Files\0*.*\0");
    if (scriptPath.empty())
    {
        std::cout << "No script selected." << std::endl;
        return;
    }

    std::string timestamp = getCurrentTimestamp();
    std::string command = "python \"" + scriptPath + "\" \"" + csvPath + "\" \"" + timestamp + "\"";
    std::cout << "Executing command: " << command << std::endl;
    int result = std::system(command.c_str());
    if (result == 0)
    {
        std::cout << "Successfully trained model using " << scriptPath << std::endl;
    }
    else
    {
        std::cerr << "Error training model using " << scriptPath << std::endl;
    }
}

void initPython()
{
    std::cout << "Initializing Python..." << std::endl;
    // Append to PYTHONPATH instead of overwriting
    const char *current_pythonpath = std::getenv("PYTHONPATH");
    std::string new_pythonpath = current_pythonpath ? std::string(current_pythonpath) + ";" : "";
    new_pythonpath += "C:/Users/papis/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/site-packages;.";
#ifdef _WIN32
    _putenv_s("PYTHONPATH", new_pythonpath.c_str());
#else
    setenv("PYTHONPATH", new_pythonpath.c_str(), 1);
#endif
    Py_Initialize();
    if (!Py_IsInitialized())
    {
        std::cerr << "Failed to initialize Python" << std::endl;
        return;
    }
    // Print Python information
    PyRun_SimpleString(
        "import sys\n"
        "import os\n"
        "print('Python version:', sys.version)\n"
        "print('Python executable:', sys.executable)\n"
        "print('Python prefix:', sys.prefix)\n"
        "print('Python path:', sys.path)\n"
        "print('Current working directory:', os.getcwd())\n"
        "print('Files in current directory:', os.listdir('.'))\n");
}
        
bool initModelSockets()
{
    const int MAX_RETRIES = 5;
    const int RETRY_DELAY_MS = 1000;
    for (auto &model : availableModels)
    {
        if (model.selected)
        {
            for (int retry = 0; retry < MAX_RETRIES; ++retry)
            {
                model.socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
                if (model.socket == INVALID_SOCKET)
                {
                    std::cerr << "Error creating socket for " << model.name << ": " << WSAGetLastError() << std::endl;
                    return false;
                }
                sockaddr_in serverAddr;
                serverAddr.sin_family = AF_INET;
                serverAddr.sin_port = htons(model.port);
                inet_pton(AF_INET, "127.0.0.1", &serverAddr.sin_addr);
                if (connect(model.socket, (SOCKADDR *)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR)
                {
                    int error = WSAGetLastError();
                    if (error == WSAEADDRINUSE)
                    {
                        std::cerr << "Address already in use for " << model.name << ". Retrying..." << std::endl;
                        closesocket(model.socket);
                        model.socket = INVALID_SOCKET;
                        std::this_thread::sleep_for(std::chrono::milliseconds(RETRY_DELAY_MS));
                        continue;
                    }
                    else
                    {
                        std::cerr << "Connect failed for " << model.name << " with error: " << error << std::endl;
                        closesocket(model.socket);
                        model.socket = INVALID_SOCKET;
                        return false;
                    }
                }
                else
                {
                    std::cout << "Successfully connected to " << model.name << " on port " << model.port << std::endl;
                    break;
                }
            }
            if (model.socket == INVALID_SOCKET)
            {
                std::cerr << "Failed to connect to " << model.name << " after " << MAX_RETRIES << " attempts" << std::endl;
                return false;
            }
        }
    }
    return true;
}
void closeModelSockets()
{
    for (auto &model : availableModels)
    {
        if (model.socket != INVALID_SOCKET)
        {
            closesocket(model.socket);
            model.socket = INVALID_SOCKET;
        }
    }
}

void terminatePythonProcesses()
{
    // Send termination command to all model sockets
    for (auto &model : availableModels)
    {
        if (model.socket != INVALID_SOCKET)
        {
            try
            {
                json terminateCmd;
                terminateCmd["command"] = "terminate";
                std::string jsonStr = terminateCmd.dump() + "\n"; // Add newline for message completion
                send(model.socket, jsonStr.c_str(), jsonStr.length(), 0);

                // Wait briefly for the command to be sent
                std::this_thread::sleep_for(std::chrono::milliseconds(100));

                // Shutdown and close socket
                shutdown(model.socket, SD_BOTH);
                closesocket(model.socket);
                model.socket = INVALID_SOCKET;
            }
            catch (...)
            {
                // Ignore cleanup errors
            }
        }
    }

    // On Windows, forcefully terminate Python processes if they're still running
#ifdef _WIN32
    std::system("taskkill /F /IM python.exe /T > nul 2>&1");
#endif
}

void stopSimulation()
{
    simulationEnded = true;
    simulationRunning = false;
    modelStats.clear();
    for (const auto &model : availableModels)
    {
        if (model.selected && model.socket != INVALID_SOCKET)
        {
            json request;
            request["command"] = "get_stats";
            std::string jsonStr = request.dump() + "\n";
            send(model.socket, jsonStr.c_str(), jsonStr.length(), 0);

            char recvbuf[1024];
            int iResult = recv(model.socket, recvbuf, 1024, 0);
            if (iResult > 0)
            {
                std::string response(recvbuf, iResult);
                json stats = json::parse(response);
                stats["model_name"] = model.name;
                modelStats.push_back(stats);
            }
        }
    }
    terminatePythonProcesses();
}

void runSimulation()
{
    std::cout << "Running simulation..." << std::endl;
    PyObject *pName, *pModule, *pFunc, *pArgs, *pQueue, *pValue;
    // Print current working directory and Python path
    PyRun_SimpleString(
        "import os\n"
        "import sys\n"
        "import queue\n"
        "print('Current working directory:', os.getcwd())\n"
        "print('Files in current directory:', os.listdir('.'))\n"
        "print('Python path:', sys.path)\n");
    pName = PyUnicode_FromString("simulation_script");
    std::cout << "A... (Created module name object)" << std::endl;
    pModule = PyImport_ImportModule("simulation_script");
    if (pModule == NULL)
    {
        PyErr_Print();
        std::cerr << "Failed to load the Python module." << std::endl;
        // Additional debugging information
        PyRun_SimpleString(
            "import sys\n"
            "import importlib.util\n"
            "import traceback\n"
            "script_path = 'simulation_script.py'\n"
            "print('Attempting to load:', script_path)\n"
            "if os.path.exists(script_path):\n"
            " print('File exists')\n"
            " with open(script_path, 'r') as f:\n"
            " print('File contents:')\n"
            " print(f.read())\n"
            " try:\n"
            " spec = importlib.util.spec_from_file_location('simulation_script', script_path)\n"
            " module = importlib.util.module_from_spec(spec)\n"
            " spec.loader.exec_module(module)\n"
            " print('Module loaded successfully')\n"
            " except Exception as e:\n"
            " print('Error loading module:', str(e))\n"
            " print('Traceback:')\n"
            " traceback.print_exc()\n"
            "else:\n"
            " print('File does not exist')\n"
            "print('Updated Python path:', sys.path)\n");
        return;
    }
    std::cout << "B... (Imported module)" << std::endl;
    pFunc = PyObject_GetAttrString(pModule, "run_simulation");
    if (pFunc && PyCallable_Check(pFunc))
    {
        std::cout << "C... (Found run_simulation function)" << std::endl;
        // Create a Python queue
        PyObject *queueModule = PyImport_ImportModule("queue");
        PyObject *queueClass = PyObject_GetAttrString(queueModule, "Queue");
        pQueue = PyObject_CallObject(queueClass, NULL);
        std::cout << "Created Python queue" << std::endl;
        // Create arguments tuple for the function call
        pArgs = PyTuple_New(3);
        PyTuple_SetItem(pArgs, 0, pQueue);
        PyTuple_SetItem(pArgs, 1, PyBool_FromLong(includeDOS));
        PyTuple_SetItem(pArgs, 2, PyLong_FromLong(12345)); // Pass the port number as the third argument
        // Call the Python function
        std::cout << "Calling run_simulation function..." << std::endl;
        pValue = PyObject_CallObject(pFunc, pArgs);
        Py_DECREF(pArgs);
        if (pValue == NULL)
        {
            PyErr_Print();
            std::cerr << "Call to run_simulation failed" << std::endl;
        }
        else
        {
            std::cout << "D... (Called run_simulation function successfully)" << std::endl;
            Py_DECREF(pValue);
        }
    }
    else
    {
        if (PyErr_Occurred())
            PyErr_Print();
        std::cerr << "Cannot find function 'run_simulation'" << std::endl;
    }
    if (PyErr_Occurred())
    {
        PyErr_Print();
        std::cerr << "Python error occurred during simulation" << std::endl;
    }
    Py_XDECREF(pFunc);
    Py_DECREF(pModule);
    std::cout << "Z... (Finished runSimulation)" << std::endl;
}

std::queue<std::vector<float>> predictionQueue;
std::mutex predictionQueueMutex;
std::atomic<bool> predictionReceiverRunning(true);

void sendDataToPredictionScript(const std::vector<float> &data)
{
    try
    {
        json j;
        j["FB"] = data[0];
        j["TB"] = data[1];
        j["IAT"] = data[2];
        j["TD"] = data[3];
        j["Arrival Time"] = data[4];
        j["PC"] = data[5];
        j["Packet Size"] = data[6];
        j["Acknowledgement Packet Size"] = data[7];
        j["RTT"] = data[8];
        j["Average Queue Size"] = data[9];
        j["System Occupancy"] = data[10];
        j["Arrival Rate"] = data[11];
        j["Service Rate"] = data[12];
        j["Packet Dropped"] = data[13];
        j["Is Attack"] = data[16]; 
        std::string jsonStr = j.dump();
        SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (sock == INVALID_SOCKET)
        {
            std::cerr << "Error creating socket for sending to prediction script: " << WSAGetLastError() << std::endl;
            return;
        }
        sockaddr_in serverAddr;
        serverAddr.sin_family = AF_INET;
        serverAddr.sin_port = htons(12347); // different port for sending to prediction script
        inet_pton(AF_INET, "127.0.0.1", &serverAddr.sin_addr);
        if (connect(sock, (SOCKADDR *)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR)
        {
            std::cerr << "Connect failed with error: " << WSAGetLastError() << std::endl;
            closesocket(sock);
            return;
        }
        if (send(sock, jsonStr.c_str(), jsonStr.length(), 0) == SOCKET_ERROR)
        {
            std::cerr << "Send failed with error: " << WSAGetLastError() << std::endl;
        }
        closesocket(sock);
    }
    catch (const std::exception &e)
    {
        std::cerr << "Error sending data to prediction script: " << e.what() << std::endl;
    }
}
bool initPredictionSocket()
{
    const int MAX_RETRIES = 10;
    const int RETRY_DELAY_MS = 500;

    for (auto &model : availableModels)
    {
        if (model.selected)
        {
            bool connected = false;
            for (int retry = 0; retry < MAX_RETRIES && !connected; ++retry)
            {
                if (retry > 0)
                {
                    std::cout << "Retry " << retry << " for " << model.name << std::endl;
                    std::this_thread::sleep_for(std::chrono::milliseconds(RETRY_DELAY_MS));
                }

                model.socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
                if (model.socket == INVALID_SOCKET)
                {
                    std::cerr << "Error creating prediction socket for " << model.name
                              << ": " << WSAGetLastError() << std::endl;
                    continue;
                }

                sockaddr_in serverAddr;
                serverAddr.sin_family = AF_INET;
                serverAddr.sin_port = htons(model.port);
                inet_pton(AF_INET, "127.0.0.1", &serverAddr.sin_addr);

                if (connect(model.socket, (SOCKADDR *)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR)
                {
                    std::cerr << "Connect attempt " << retry + 1 << " failed for " << model.name
                              << " with error: " << WSAGetLastError() << std::endl;
                    closesocket(model.socket);
                    model.socket = INVALID_SOCKET;
                    continue;
                }

                std::cout << "Successfully connected to " << model.name
                          << " on port " << model.port << std::endl;
                connected = true;
            }

            if (!connected)
            {
                std::cerr << "Failed to connect to " << model.name
                          << " after " << MAX_RETRIES << " attempts" << std::endl;
                return false;
            }
        }
    }
    return true;
}
float getPredictionFromPython(const std::vector<float> &data, const std::string &modelName)
{
    auto it = std::find_if(availableModels.begin(), availableModels.end(),
                           [&modelName](const ModelInfo &model)
                           { return model.name == modelName; });
    if (it == availableModels.end() || it->socket == INVALID_SOCKET)
    {
        std::cerr << "Invalid socket for " << modelName << std::endl;
        return 0.0f;
    }
    json j;
    j["model"] = modelName;
    j["IAT"] = data[2];
    j["TD"] = data[3];
    j["Arrival Time"] = data[4];
    j["PC"] = data[5];
    j["Packet Size"] = data[6];
    j["Acknowledgement Packet Size"] = data[7];
    j["RTT"] = data[8];
    j["Average Queue Size"] = data[9];
    j["System Occupancy"] = data[10];
    j["Arrival Rate"] = data[11];
    j["Service Rate"] = data[12];
    j["Packet Dropped"] = data[13];
    j["Is Attack"] = data[16];
    std::string jsonStr = j.dump();
    if (send(it->socket, jsonStr.c_str(), jsonStr.length(), 0) == SOCKET_ERROR)
    {
        std::cerr << "Send failed for " << modelName << " with error: " << WSAGetLastError() << std::endl;
        return 0.0f;
    }
    char recvbuf[1024];
    int iResult = recv(it->socket, recvbuf, 1024, 0);
    if (iResult > 0)
    {
        std::string response(recvbuf, iResult);
        json responseJson = json::parse(response);
        return responseJson["prediction"].get<float>();
    }
    else if (iResult == 0)
    {
        std::cout << "Connection closed for " << modelName << std::endl;
    }
    else
    {
        std::cerr << "Recv failed for " << modelName << " with error: " << WSAGetLastError() << std::endl;
    }
    return 0.0f;
}

void processData()
{
    std::lock_guard<std::mutex> lock(queueMutex);
    while (!dataQueue.empty())
    {
        std::vector<float> data = dataQueue.front();
        dataQueue.pop();

        if (data.size() >= 20)
        {
            int fb = static_cast<int>(data[0]);
            int tb = static_cast<int>(data[1]);
            std::pair<int, int> connection(fb, tb);

            if (fbTbCombinations.find(connection) == fbTbCombinations.end())
            {
                fbTbCombinations[connection] = fbTbCombinations.size();
            }

            // Create AttackInfo structure
            AttackInfo attackInfo;
            attackInfo.none = data[16] > 0.5f;
            attackInfo.ddos = data[17] > 0.5f;
            attackInfo.synflood = data[18] > 0.5f;
            attackInfo.mitm = data[19] > 0.5f;

            std::cout << "Received data point with " << data.size() << " elements" << std::endl;
            std::cout << "CPP DATA ENQUEUE [ ";
            for (const auto &value : data)
            {
                std::cout << value << " ";
            }
            std::cout << "]" << std::endl;

            // Process all metrics
            for (int i = 0; i < metricLabels.size(); ++i)
            {
                std::lock_guard<std::mutex> lock(plotDataMutexes[i]);
                float value = 0.0f;
                switch (i)
                {
                case 0: // Packets Dropped
                    value = data[13];
                    break;
                case 1: // Average Queue Size
                    value = data[9];
                    break;
                case 2: // System Occupancy
                    value = data[10];
                    break;
                case 3: // Service Rate
                    value = data[12];
                    break;
                case 4: // Transmission Delay
                    value = data[3];
                    break;
                case 5: // Round Trip Time (RTT)
                    value = data[8];
                    break;
                case 6: // Arrival Rate
                    value = data[11];
                    break;
                case 7: // Attack Type Distribution
                    if (attackInfo.ddos)
                        value = 1.0f;
                    else if (attackInfo.synflood)
                        value = 2.0f;
                    else if (attackInfo.mitm)
                        value = 3.0f;
                    else
                        value = 0.0f;
                    break;
                case 8: // Packet Size
                    value = data[6];
                    break;
                case 9: // IAT
                    value = data[2];
                    break;
                case 10: // Acknowledgement Size
                    value = data[7];
                    break;
                case 11: // Packet Count (PC)
                    value = data[5];
                    
                    break;
                default:
                    value = 0.0f;
                }
                plotDataArray[i].values[connection].push_back(value);

                // Limit data points for each metric
                if (plotDataArray[i].values[connection].size() > 1000)
                {
                    plotDataArray[i].values[connection].erase(
                        plotDataArray[i].values[connection].begin());
                }
            }

            // Process model predictions
            for (auto &model : availableModels)
            {
                if (model.selected)
                {
                    // Create prediction request
                    json predictionRequest;
                    predictionRequest["IAT"] = data[2];
                    predictionRequest["TD"] = data[3];
                    predictionRequest["Arrival Time"] = data[4];
                    predictionRequest["PC"] = data[5];
                    predictionRequest["Packet Size"] = data[6];
                    predictionRequest["Acknowledgement Packet Size"] = data[7];
                    predictionRequest["RTT"] = data[8];
                    predictionRequest["Average Queue Size"] = data[9];
                    predictionRequest["System Occupancy"] = data[10];
                    predictionRequest["Arrival Rate"] = data[11];
                    predictionRequest["Service Rate"] = data[12];
                    predictionRequest["Packet Dropped"] = data[13];
                    predictionRequest["attack_none"] = attackInfo.none;
                    predictionRequest["attack_ddos"] = attackInfo.ddos;
                    predictionRequest["attack_synflood"] = attackInfo.synflood;
                    predictionRequest["attack_mitm"] = attackInfo.mitm;

                    std::string jsonStr = predictionRequest.dump();
                    if (send(model.socket, jsonStr.c_str(), jsonStr.length(), 0) != SOCKET_ERROR)
                    {
                        char recvbuf[1024];
                        int iResult = recv(model.socket, recvbuf, 1024, 0);
                        if (iResult > 0)
                        {
                            std::string response(recvbuf, iResult);
                            json responseJson = json::parse(response);
                            float prediction = responseJson["prediction"].get<float>();
                            model.plotData[0].values[connection].push_back(prediction);
                        }
                    }
                }
            }
        }
    }
}

void simulationThread()
{
    try
    {
        PyObject *pName, *pModule, *pFunc, *pArgs, *pValue;
        pName = PyUnicode_FromString("simulation_script");
        pModule = PyImport_ImportModule("simulation_script");
        if (pModule == NULL)
        {
            PyErr_Print();
            std::cerr << "Failed to load the Python module." << std::endl;
            simulationEnded = true;
            return;
        }

        pFunc = PyObject_GetAttrString(pModule, "run_simulation");
        if (pFunc && PyCallable_Check(pFunc))
        {
            pArgs = PyTuple_New(5);

            // Convert traffic type to corresponding AttackType value
            PyObject *attackType;
            switch (currentTrafficType)
            {
            case TrafficType::NORMAL:
                attackType = PyLong_FromLong(0);
                break;
            case TrafficType::DDOS:
                attackType = PyLong_FromLong(1);
                break;
            case TrafficType::SYN_FLOOD:
                attackType = PyLong_FromLong(2); // AttackType.SYN_FLOOD
                break;
            case TrafficType::MITM_SCADA:
                attackType = PyLong_FromLong(3);
                break;
            default:
                attackType = PyLong_FromLong(0);
            }

            PyTuple_SetItem(pArgs, 0, PyLong_FromLong(12345)); // port
            PyTuple_SetItem(pArgs, 1, attackType);
            PyTuple_SetItem(pArgs, 2, PyLong_FromLong(totalSimulationTime));
            PyTuple_SetItem(pArgs, 3, PyLong_FromLong(dosAttackTime));
            PyTuple_SetItem(pArgs, 4, PyBool_FromLong(true)); // start_simulation flag

            pValue = PyObject_CallObject(pFunc, pArgs);
            Py_DECREF(pArgs);

            if (pValue == NULL)
            {
                PyErr_Print();
                std::cerr << "Call to run_simulation failed" << std::endl;
            }
            else
            {
                Py_DECREF(pValue);
            }
        }

        Py_XDECREF(pFunc);
        Py_DECREF(pModule);

        while (!dataQueue.empty())
        {
            processData();
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }
    catch (const std::exception &e)
    {
        std::cerr << "Exception in simulation thread: " << e.what() << std::endl;
    }

    simulationRunning = false;
    simulationEnded = true;
    stopSimulation();
}


void handleGlobalScroll(float newScrollX, bool fromPlot)
{
    if (!isScrolling)
    {
        isScrolling = true;
        globalScrollX = newScrollX;
        scrollFromPlot = fromPlot;

        // Update all metric plots
        for (size_t i = 0; i < metricLabels.size(); ++i)
        {
            if (plotVisibility[i])
            {
                ImGuiWindow *window = ImGui::FindWindowByName(("ScrollingRegion##" + std::to_string(i)).c_str());
                if (window)
                {
                    window->Scroll.x = globalScrollX;
                }
            }
        }

        // Update all model plots
        for (const auto &model : availableModels)
        {
            if (model.selected)
            {
                ImGuiWindow *window = ImGui::FindWindowByName(("ScrollingRegion##" + model.name).c_str());
                if (window)
                {
                    window->Scroll.x = globalScrollX;
                }
            }
        }

        isScrolling = false;
        scrollFromPlot = false;
    }
}

void renderPlots()
{
    ImPlotFlags flags = ImPlotFlags_NoMouseText;
    ImPlotAxisFlags axes_flags = ImPlotAxisFlags_NoTickLabels;
    const int VISIBLE_POINTS = 100;
    static std::vector<bool> showLegends(metricLabels.size(), false);

    for (size_t i = 0; i < metricLabels.size(); ++i)
    {
        if (plotVisibility[i])
        {
            ImGui::BeginChild(metricLabels[i].c_str(), ImVec2(0, 250), true);

            ImGui::Text("%s", metricLabels[i].c_str());
            ImGui::SameLine(ImGui::GetWindowWidth() - 70);
            std::string buttonLabel = (showLegends[i] ? "Hide" : "Show");
            buttonLabel += " Legend##";
            buttonLabel += std::to_string(i);
            if (ImGui::Button(buttonLabel.c_str()))
            {
                showLegends[i] = !showLegends[i];
            }

            int maxDataLength = 0;
            for (const auto &[connection, values] : plotDataArray[i].values)
            {
                maxDataLength = std::max(maxDataLength, static_cast<int>(values.size()));
            }

            float plotWidth = ImGui::GetContentRegionAvail().x;
            float totalWidth = std::max(plotWidth, (maxDataLength * plotWidth) / VISIBLE_POINTS);

            ImGui::BeginChild(("ScrollingRegion##" + std::to_string(i)).c_str(),
                              ImVec2(0, 200), true,
                              ImGuiWindowFlags_HorizontalScrollbar);

            float currentScroll = ImGui::GetScrollX();
            if (!scrollFromPlot && std::abs(currentScroll - globalScrollX) > 1.0f)
            {
                handleGlobalScroll(currentScroll, true);
            }
            else
            {
                ImGui::SetScrollX(globalScrollX);
            }

            if (simulationRunning && maxDataLength > VISIBLE_POINTS)
            {
                float maxScroll = ImGui::GetScrollMaxX();
                handleGlobalScroll(maxScroll, true);
            }

            ImPlotFlags plot_flags = flags | ImPlotFlags_NoLegend;
            if (showLegends[i])
            {
                plot_flags &= ~ImPlotFlags_NoLegend;
            }

            if (ImPlot::BeginPlot((metricLabels[i] + "##plot").c_str(),
                                  ImVec2(totalWidth, -1),
                                  plot_flags))
            {
                ImPlot::SetupAxes("Data Point", metricLabels[i].c_str(), axes_flags, axes_flags);

                float scrollX = ImGui::GetScrollX();
                int startPoint = static_cast<int>((scrollX / totalWidth) * maxDataLength);
                int endPoint = startPoint + VISIBLE_POINTS;

                double y_min = std::numeric_limits<double>::max();
                double y_max = std::numeric_limits<double>::lowest();

                for (const auto &[connection, values] : plotDataArray[i].values)
                {
                    if (!values.empty())
                    {
                        size_t endIdx = std::min<size_t>(endPoint, values.size());
                        size_t startIdx = std::min<size_t>(startPoint, values.size());

                        if (startIdx < endIdx)
                        {
                            auto start_it = values.begin() + startIdx;
                            auto end_it = values.begin() + endIdx;
                            y_min = std::min(y_min, static_cast<double>(*std::min_element(start_it, end_it)));
                            y_max = std::max(y_max, static_cast<double>(*std::max_element(start_it, end_it)));
                        }
                    }
                }

                if (i == 7)
                {
                    y_min = -0.2;
                    y_max = 1.2;
                }
                else if (y_min != std::numeric_limits<double>::max())
                {
                    double y_range = y_max - y_min;
                    y_min -= y_range * 0.1;
                    y_max += y_range * 0.1;
                }

                ImPlot::SetupAxisLimits(ImAxis_X1, startPoint, endPoint, ImGuiCond_Always);
                ImPlot::SetupAxisLimits(ImAxis_Y1, y_min, y_max, ImGuiCond_Always);

                for (const auto &[connection, values] : plotDataArray[i].values)
                {
                    if (!values.empty())
                    {
                        std::string label = "FB" + std::to_string(connection.first) +
                                            " -> TB" + std::to_string(connection.second);

                        size_t endIdx = std::min<size_t>(endPoint, values.size());
                        size_t startIdx = std::min<size_t>(startPoint, values.size());

                        if (startIdx < endIdx)
                        {
                            std::vector<double> x_values;
                            std::vector<double> y_values;
                            x_values.reserve(endIdx - startIdx);
                            y_values.reserve(endIdx - startIdx);

                            for (size_t j = startIdx; j < endIdx; ++j)
                            {
                                x_values.push_back(static_cast<double>(j));
                                if (i == 7) // Attack Type plot
                                {
                                    int attackType = static_cast<int>(values[j]);
                                    ImPlot::SetNextMarkerStyle(ImPlotMarker_Square, 4, ATTACK_COLORS[attackType]);
                                    ImPlot::PlotScatter(label.c_str(),
                                                        &x_values.back(),
                                                        &(y_values.emplace_back(attackType == 0 ? 0.0 : 1.0)),
                                                        1);
                                }
                                else // Other metrics
                                {
                                    y_values.push_back(static_cast<double>(values[j]));
                                }
                            }

                            if (i != 7) // Line plots for non-attack metrics
                            {
                                ImPlot::SetNextLineStyle(colors[fbTbCombinations[connection] % MAX_LINES]);
                                ImPlot::PlotLine(label.c_str(),
                                                 x_values.data(),
                                                 y_values.data(),
                                                 static_cast<int>(y_values.size()));
                            }
                        }
                    }
                }
                ImPlot::EndPlot();
            }

            ImGui::EndChild(); // End scrolling region
            ImGui::EndChild(); // End main child
        }
    }
}

void renderModelPlots()
{
    ImPlotFlags flags = ImPlotFlags_NoMouseText;
    ImPlotAxisFlags axes_flags = ImPlotAxisFlags_NoTickLabels;
    const int VISIBLE_POINTS = 100;
    static std::vector<bool> showLegends(availableModels.size(), false);

    for (const auto &model : availableModels)
    {
        if (model.selected)
        {
            std::string plotLabel = model.name + " Prediction";
            ImGui::BeginChild(plotLabel.c_str(), ImVec2(0, 250), true);

            ImGui::Text("%s", plotLabel.c_str());
            ImGui::SameLine(ImGui::GetWindowWidth() - 70);
            std::string buttonLabel = (showLegends[&model - &availableModels[0]] ? "Hide" : "Show");
            buttonLabel += " Legend##";
            buttonLabel += model.name;
            if (ImGui::Button(buttonLabel.c_str()))
            {
                showLegends[&model - &availableModels[0]] = !showLegends[&model - &availableModels[0]];
            }

            if (showLegends[&model - &availableModels[0]])
            {
                ImGui::ColorButton("##Normal", ATTACK_COLORS[0], 0, ImVec2(15, 15));
                ImGui::SameLine();
                ImGui::Text("Normal");
                ImGui::SameLine(100);
                ImGui::ColorButton("##DDoS", ATTACK_COLORS[1], 0, ImVec2(15, 15));
                ImGui::SameLine();
                ImGui::Text("DDoS");
                ImGui::SameLine(200);
                ImGui::ColorButton("##SYN", ATTACK_COLORS[2], 0, ImVec2(15, 15));
                ImGui::SameLine();
                ImGui::Text("SYN Flood");
                ImGui::SameLine(300);
                ImGui::ColorButton("##MITM", ATTACK_COLORS[3], 0, ImVec2(15, 15));
                ImGui::SameLine();
                ImGui::Text("MITM");
            }

            int maxDataLength = 0;
            for (const auto &[connection, values] : model.plotData[0].values)
            {
                maxDataLength = std::max(maxDataLength, static_cast<int>(values.size()));
            }

            float plotWidth = ImGui::GetContentRegionAvail().x;
            float totalWidth = std::max(plotWidth, (maxDataLength * plotWidth) / VISIBLE_POINTS);

            ImGui::BeginChild(("ScrollingRegion##" + model.name).c_str(),
                              ImVec2(0, 200), true,
                              ImGuiWindowFlags_HorizontalScrollbar);

            float currentScroll = ImGui::GetScrollX();
            if (!scrollFromPlot && std::abs(currentScroll - globalScrollX) > 1.0f)
            {
                handleGlobalScroll(currentScroll, true);
            }
            else
            {
                ImGui::SetScrollX(globalScrollX);
            }

            if (simulationRunning && maxDataLength > VISIBLE_POINTS)
            {
                float maxScroll = ImGui::GetScrollMaxX();
                handleGlobalScroll(maxScroll, true);
            }

            ImPlotFlags plot_flags = flags | ImPlotFlags_NoLegend;
            if (showLegends[&model - &availableModels[0]])
            {
                plot_flags &= ~ImPlotFlags_NoLegend;
            }

            if (ImPlot::BeginPlot(plotLabel.c_str(), ImVec2(totalWidth, -1), plot_flags))
            {
                ImPlot::SetupAxes("Data Point", "Attack Detection", axes_flags, axes_flags);

                float scrollX = ImGui::GetScrollX();
                int startPoint = static_cast<int>((scrollX / totalWidth) * maxDataLength);
                int endPoint = startPoint + VISIBLE_POINTS;

                ImPlot::SetupAxisLimits(ImAxis_X1, startPoint, endPoint, ImGuiCond_Always);
                ImPlot::SetupAxisLimits(ImAxis_Y1, -0.2, 1.2, ImGuiCond_Always);

                for (const auto &[connection, values] : model.plotData[0].values)
                {
                    if (!values.empty())
                    {
                        std::string label = "FB" + std::to_string(connection.first) +
                                            " -> TB" + std::to_string(connection.second);

                        size_t endIdx = std::min<size_t>(endPoint, values.size());
                        size_t startIdx = std::min<size_t>(startPoint, values.size());

                        if (startIdx < endIdx)
                        {
                            for (size_t j = startIdx; j < endIdx; ++j)
                            {
                                double x = static_cast<double>(j);
                                double y = values[j] >= 0.5 ? 1.0 : 0.0;

                                // Determine point color based on prediction value
                                ImVec4 pointColor;
                                if (values[j] >= 0.9) // MITM
                                    pointColor = ATTACK_COLORS[3];
                                else if (values[j] >= 0.7) // SYN Flood
                                    pointColor = ATTACK_COLORS[2];
                                else if (values[j] >= 0.5) // DDoS
                                    pointColor = ATTACK_COLORS[1];
                                else // Normal
                                    pointColor = ATTACK_COLORS[0];

                                ImPlot::SetNextMarkerStyle(ImPlotMarker_Square, 4, pointColor);
                                ImPlot::PlotScatter(label.c_str(), &x, &y, 1);
                            }
                        }
                    }
                }
                ImPlot::EndPlot();
            }

            ImGui::EndChild(); // End scrolling region

            // Show accuracy information only when legend is enabled
            if (showLegends[&model - &availableModels[0]])
            {
                ImGui::Text("Detection Accuracy by Attack Type:");
                ImGui::Indent();
                for (const auto &[attackType, accuracy] : model.attackAccuracy)
                {
                    const char *attackName = "";
                    switch (attackType)
                    {
                    case AttackType::NONE:
                        attackName = "Normal";
                        break;
                    case AttackType::DDOS:
                        attackName = "DDoS";
                        break;
                    case AttackType::SYN_FLOOD:
                        attackName = "SYN Flood";
                        break;
                    case AttackType::MITM_SCADA:
                        attackName = "MITM";
                        break;
                    }
                    ImGui::Text("%s: %.2f%%", attackName, accuracy * 100.0f);
                }
                ImGui::Unindent();
            }

            ImGui::EndChild(); // End main child
        }
    }
}

void receiveDataFromPython()
{
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        std::cerr << "WSAStartup failed.\n";
        return;
    }
    
    listenSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listenSocket == INVALID_SOCKET)
    {
        std::cerr << "Error creating socket: " << WSAGetLastError() << std::endl;
        WSACleanup();
        return;
    }

    // Set socket to non-blocking mode
    u_long mode = 1;
    ioctlsocket(listenSocket, FIONBIO, &mode);

    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(12345);

    // Add SO_REUSEADDR option
    int opt = 1;
    setsockopt(listenSocket, SOL_SOCKET, SO_REUSEADDR, (char *)&opt, sizeof(opt));

    if (bind(listenSocket, (SOCKADDR *)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR)
    {
        std::cerr << "Bind failed with error: " << WSAGetLastError() << std::endl;
        closesocket(listenSocket);
        WSACleanup();
        return;
    }

    if (listen(listenSocket, SOMAXCONN) == SOCKET_ERROR)
    {
        std::cerr << "Listen failed with error: " << WSAGetLastError() << std::endl;
        closesocket(listenSocket);
        WSACleanup();
        return;
    }

    std::vector<SOCKET> clientSockets;

    while (!shouldExit)
    {
        if (receiverRunning)
        {
            fd_set readSet;
            FD_ZERO(&readSet);
            FD_SET(listenSocket, &readSet);

            for (const auto &sock : clientSockets)
            {
                FD_SET(sock, &readSet);
            }

            // Set timeout for select
            timeval timeout;
            timeout.tv_sec = 0;
            timeout.tv_usec = 100000; // 100ms timeout

            int result = select(0, &readSet, nullptr, nullptr, &timeout);

            if (result > 0)
            {
                // Check for new connections
                if (FD_ISSET(listenSocket, &readSet))
                {
                    SOCKET clientSocket = accept(listenSocket, NULL, NULL);
                    if (clientSocket != INVALID_SOCKET)
                    {
                        clientSockets.push_back(clientSocket);
                    }
                }

                // Check existing connections
                for (auto it = clientSockets.begin(); it != clientSockets.end();)
                {
                    if (FD_ISSET(*it, &readSet))
                    {
                        char recvbuf[1024];
                        int iResult = recv(*it, recvbuf, 1024, 0);

                        if (iResult > 0)
                        {
                            // Process received data
                            std::string receivedData(recvbuf, iResult);
                            try
                            {
                                json j = json::parse(receivedData);
                                std::vector<float> dataPoint;
                                for (const auto &[key, value] : j.items())
                                {
                                    if (value.is_number())
                                    {
                                        dataPoint.push_back(value.get<float>());
                                    }
                                    else
                                    {
                                        dataPoint.push_back(0.0f);
                                    }
                                }
                                std::lock_guard<std::mutex> lock(queueMutex);
                                dataQueue.push(dataPoint);
                            }
                            catch (const json::parse_error &e)
                            {
                                std::cerr << "JSON parse error: " << e.what() << std::endl;
                            }
                            ++it;
                        }
                        else
                        {
                            // Connection closed or error
                            closesocket(*it);
                            it = clientSockets.erase(it);
                        }
                    }
                    else
                    {
                        ++it;
                    }
                }
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }

    // Cleanup client sockets
    for (SOCKET sock : clientSockets)
    {
        closesocket(sock);
    }

    if (listenSocket != INVALID_SOCKET)
    {
        closesocket(listenSocket);
        listenSocket = INVALID_SOCKET;
    }

    WSACleanup();
}

void saveModelAndStatistics(const ModelInfo &model, const json &stats)
{
    sqlite3 *db;
    char *zErrMsg = 0;
    int rc;
    rc = sqlite3_open("model_database.db", &db);
    if (rc)
    {
        std::cerr << "Can't open database: " << sqlite3_errmsg(db) << std::endl;
        return;
    }

    // Create the model_runs table if it doesn't exist
    const char *sql_create = "CREATE TABLE IF NOT EXISTS model_runs ("
                             "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                             "model_name TEXT NOT NULL,"
                             "model_file_path TEXT NOT NULL,"
                             "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,"
                             "total_predictions INTEGER NOT NULL,"
                             "accuracy REAL NOT NULL,"
                             "precision REAL NOT NULL,"
                             "recall REAL NOT NULL,"
                             "f1_score REAL NOT NULL);";
    rc = sqlite3_exec(db, sql_create, NULL, 0, &zErrMsg);
    if (rc != SQLITE_OK)
    {
        std::cerr << "SQL error: " << zErrMsg << std::endl;
        sqlite3_free(zErrMsg);
    }

    // Create a timestamped folder
    std::string timestamp = std::to_string(std::time(nullptr));
    std::filesystem::path saveDir = "saved_models/" + timestamp;
    std::filesystem::create_directories(saveDir);

    // Save the model file
    std::string modelFilename = model.name + ".pkl";
    std::filesystem::path modelPath = saveDir / modelFilename;

    // Send a command to the Python script to save the model
    json saveCommand;
    saveCommand["command"] = "save_model";
    saveCommand["path"] = modelPath.string();
    std::string jsonStr = saveCommand.dump();
    if (send(model.socket, jsonStr.c_str(), jsonStr.length(), 0) == SOCKET_ERROR)
    {
        std::cerr << "Failed to send save command to Python script" << std::endl;
        return;
    }

    // Wait for response from Python script
    char recvbuf[1024];
    int iResult = recv(model.socket, recvbuf, 1024, 0);
    if (iResult > 0)
    {
        std::string response(recvbuf, iResult);
        json responseJson = json::parse(response);
        if (responseJson["status"] != "success")
        {
            std::cerr << "Failed to save model: " << responseJson["message"] << std::endl;
            return;
        }
        std::cout << "Model saved successfully to " << modelPath << std::endl;
    }
    else
    {
        std::cerr << "Failed to receive response from Python script" << std::endl;
        return;
    }

    // Copy network_traffic.csv to the timestamped folder
    std::filesystem::path csvSource = "network_traffic.csv";
    std::filesystem::path csvDest = saveDir / "network_traffic.csv";
    try
    {
        std::filesystem::copy_file(csvSource, csvDest, std::filesystem::copy_options::overwrite_existing);
        std::cout << "Copied network_traffic.csv to " << csvDest << std::endl;
    }
    catch (const std::filesystem::filesystem_error &e)
    {
        std::cerr << "Error copying network_traffic.csv: " << e.what() << std::endl;
    }

    // Insert the data into the database
    const char *sql_insert = "INSERT INTO model_runs (model_name, model_file_path, total_predictions, accuracy, precision, recall, f1_score) "
                             "VALUES (?, ?, ?, ?, ?, ?, ?);";
    sqlite3_stmt *stmt;
    rc = sqlite3_prepare_v2(db, sql_insert, -1, &stmt, NULL);
    if (rc != SQLITE_OK)
    {
        std::cerr << "SQL error: " << sqlite3_errmsg(db) << std::endl;
        return;
    }

    sqlite3_bind_text(stmt, 1, model.name.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, modelPath.string().c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_int(stmt, 3, stats["total_predictions"].get<int>());
    sqlite3_bind_double(stmt, 4, stats["accuracy"].get<double>());
    sqlite3_bind_double(stmt, 5, stats["precision"].get<double>());
    sqlite3_bind_double(stmt, 6, stats["recall"].get<double>());
    sqlite3_bind_double(stmt, 7, stats["f1_score"].get<double>());

    rc = sqlite3_step(stmt);
    if (rc != SQLITE_DONE)
    {
        std::cerr << "SQL error: " << sqlite3_errmsg(db) << std::endl;
    }
    else
    {
        std::cout << "Statistics saved to database successfully" << std::endl;
    }

    sqlite3_finalize(stmt);
    sqlite3_close(db);
}

void windowCloseCallback(GLFWwindow *window)
{
    if (simulationRunning || !simulationEnded)
    {
        stopSimulation();
    }

    shouldExit = true;
    receiverRunning = false;
    applicationClosing = true;
    stopSimulationRequested = true;

    // Force cleanup of any remaining Python processes
    terminatePythonProcesses();
}

float globalScale = 1.0f;
bool initialScaleSet = false;

void setDefaultScale(GLFWwindow *window)
{
    // Get the primary monitor
    GLFWmonitor *monitor = glfwGetPrimaryMonitor();
    if (monitor)
    {
        // Get the content scale for the primary monitor
        float xscale, yscale;
        glfwGetMonitorContentScale(monitor, &xscale, &yscale);

        // Use the larger scale factor
        globalScale = std::max(xscale, yscale);

        // Get framebuffer size and window size to calculate pixel ratio
        int fbWidth, fbHeight, winWidth, winHeight;
        glfwGetFramebufferSize(window, &fbWidth, &fbHeight);
        glfwGetWindowSize(window, &winWidth, &winHeight);
        float pixelRatio = static_cast<float>(fbWidth) / winWidth;

        // Adjust scale based on pixel ratio
        globalScale *= pixelRatio;

        // Clamp to reasonable values
        globalScale = std::max(1.0f, std::min(globalScale, 3.0f));
    }
}

void startWiresharkCapture()
{
    std::cout << "Starting Wireshark capture..." << std::endl;

    // Get the path to the Python interpreter and script
    char exePath[MAX_PATH];
    GetModuleFileNameA(NULL, exePath, MAX_PATH);
    std::filesystem::path executablePath = std::filesystem::path(exePath).parent_path();
    std::filesystem::path scriptPath = executablePath / "wireshark_capture.py";

    // Create the command string
    std::string command = "python \"" + scriptPath.string() + "\" 3 12345";
    std::cout << "Executing command: " << command << std::endl;

    // Execute the Python script as a separate process
    int result = std::system(command.c_str());
    if (result == 0)
    {
        std::cout << "Wireshark capture started successfully" << std::endl;
    }
    else
    {
        std::cerr << "Error starting Wireshark capture" << std::endl;
    }
}

void stopWiresharkCapture()
{
    if (wiresharkThread.joinable())
    {
        wiresharkThread.join();
    }
    wiresharkRunning = false;
}

int main(int, char **)
{
    if (!glfwInit())
        return 1;

    GLFWwindow *window = glfwCreateWindow(1280, 720, "Real-time Network Visualization", NULL, NULL);
    if (window == NULL)
    {
        glfwTerminate();
        return 1;
    }

    glfwSetWindowCloseCallback(window, windowCloseCallback);
    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImPlot::CreateContext();
    ImGuiIO &io = ImGui::GetIO();
    (void)io;

    ImGui::StyleColorsDark();
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 130");

    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        std::cerr << "WSAStartup failed.\n";
        return 1;
    }

    initPython();
    initAvailableModels();

    shouldExit = false;
    applicationClosing = false;
    simulationRunning = false;
    simulationEnded = false;
    receiverRunning = true;
    wiresharkRunning = false;

    std::thread receiverThread(receiveDataFromPython);

    char exePath[MAX_PATH];
    GetModuleFileNameA(NULL, exePath, MAX_PATH);
    std::filesystem::path executablePath = std::filesystem::path(exePath).parent_path();

    while (!shouldExit && !glfwWindowShouldClose(window))
    {
        glfwPollEvents();

        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplGlfw_NewFrame();
        ImGui::NewFrame();

        ImGui::SetNextWindowPos(ImVec2(0, 0));
        ImGui::SetNextWindowSize(ImGui::GetIO().DisplaySize);
        ImGui::Begin("Real-time Network Visualization", nullptr,
                     ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoResize |
                         ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoBringToFrontOnFocus |
                         ImGuiWindowFlags_NoNavFocus);

        // Data Source Selection
        ImGui::Text("Data Source:");
        const char *sources[] = {"Simulation", "Wireshark Capture"};
        static int currentSourceIndex = 0;

        if (ImGui::Combo("Source", &currentSourceIndex, sources, IM_ARRAYSIZE(sources)))
        {
            currentDataSource = static_cast<DataSource>(currentSourceIndex);
            if (simulationRunning)
            {
                stopSimulation();
            }
            if (wiresharkRunning)
            {
                stopWiresharkCapture();
            }
        }

        // Model Loading Controls
        if (ImGui::Button("Load Model"))
        {
            loadModel();
        }
        ImGui::SameLine();
        if (fileExists("network_traffic.csv"))
        {
            if (ImGui::Button("Train Model"))
            {
                trainModel(std::filesystem::absolute("network_traffic.csv").string());
            }
        }

        // Model Selection
        {
            std::lock_guard<std::mutex> lock(modelsMutex);
            ImGui::Text("Available Models:");
            for (auto &model : availableModels)
            {
                ImGui::Checkbox(model.name.c_str(), &model.selected);
            }
        }

        if (currentDataSource == DataSource::SIMULATION)
        {
            // Simulation Parameters
            ImGui::Spacing();
            ImGui::Separator();
            ImGui::Text("Simulation Parameters:");
            ImGui::InputInt("Total Simulation Time (s)", &totalSimulationTime);
            if (includeDOS)
            {
                ImGui::InputInt("Attack Duration (s)", &dosAttackTime);
                if (dosAttackTime > totalSimulationTime)
                    dosAttackTime = totalSimulationTime;
            }

            // Traffic Type Selection
            const char *trafficTypes[] = {
                "Normal Traffic",
                "DDoS Traffic",
                "SYN Flood Traffic",
                "MITM Traffic"};

            static int currentTrafficIndex = 0;
            if (ImGui::Combo("Traffic Type", &currentTrafficIndex, trafficTypes, IM_ARRAYSIZE(trafficTypes)))
            {
                currentTrafficType = static_cast<TrafficType>(currentTrafficIndex);
            }

            // Simulation Control Buttons
            if (!simulationEnded)
            {
                if (simulationRunning)
                {
                    if (ImGui::Button("Stop Simulation"))
                    {
                        stopSimulationRequested = true;
                    }
                }
                else
                {
                    // Working version (simulation):
                    if (ImGui::Button("Start Simulation"))
                    {
                        simulationRunning = true;
                        stopSimulationRequested = false;
                        std::lock_guard<std::mutex> lock(modelsMutex);

                        // Clear existing threads
                        for (auto &thread : pythonScriptThreads)
                        {
                            if (thread.joinable())
                            {
                                thread.join();
                            }
                        }
                        pythonScriptThreads.clear();

                        // Start prediction scripts
                        for (auto &model : availableModels)
                        {
                            if (model.selected)
                            {
                                pythonScriptThreads.emplace_back([&model, &executablePath]()
                                                                 {
                if (!applicationClosing)
                {
                    std::filesystem::path scriptPath = executablePath / "prediction_script.py";
                    std::string modelPath = model.path.empty() ? 
                        (executablePath / model.name).string() : model.path;
                    
                    // Quotes around paths to handle spaces
                    std::string command = "python \"" + scriptPath.string() + "\" "
                                        "\"" + modelPath + "\" " 
                                        + std::to_string(model.port);
                    
                    std::cout << "Executing command: " << command << std::endl;
                    std::system(command.c_str());
                } });
                            }
                        }

                        // Wait longer for prediction scripts to start
                        std::cout << "Waiting for prediction scripts to initialize..." << std::endl;
                        std::this_thread::sleep_for(std::chrono::seconds(3));

                        // Initialize sockets with retries
                        int socketRetries = 0;
                        const int MAX_SOCKET_RETRIES = 3;
                        bool socketsInitialized = false;

                        while (!socketsInitialized && socketRetries < MAX_SOCKET_RETRIES)
                        {
                            if (socketRetries > 0)
                            {
                                std::cout << "Retrying socket initialization, attempt "
                                          << socketRetries + 1 << "..." << std::endl;
                                std::this_thread::sleep_for(std::chrono::seconds(1));
                            }

                            if (initPredictionSocket())
                            {
                                socketsInitialized = true;
                                std::cout << "All prediction sockets initialized successfully" << std::endl;
                            }
                            else
                            {
                                socketRetries++;
                            }
                        }

                        if (!socketsInitialized)
                        {
                            std::cerr << "Failed to initialize prediction sockets. Stopping simulation." << std::endl;
                            simulationRunning = false;

                            // Cleanup any started processes
                            terminatePythonProcesses();
                        }
                        else
                        {
                            // Start simulation thread
                            std::thread(simulationThread).detach();
                        }
                    }
                }
            }
        }
        else // Wireshark Capture
        {
            if (!wiresharkRunning)
            {
                if (ImGui::Button("Start Capture"))
                {
                    wiresharkRunning = true;
                    simulationRunning = true;

                    // Clear existing data
                    dataQueue = std::queue<std::vector<float>>();
                    for (auto &plotData : plotDataArray)
                    {
                        plotData.values.clear();
                    }
                    fbTbCombinations.clear();

                    // Initialize prediction scripts for models
                    std::lock_guard<std::mutex> lock(modelsMutex);
                    for (auto &thread : pythonScriptThreads)
                    {
                        if (thread.joinable())
                        {
                            thread.join();
                        }
                    }
                    pythonScriptThreads.clear();

                    for (auto &model : availableModels)
                    {
                        if (model.selected)
                        {
                            pythonScriptThreads.emplace_back([&model, &executablePath]()
                                                             {
                    if (!applicationClosing)
                    {
                        std::filesystem::path scriptPath = executablePath / "prediction_script.py";
                        std::string modelPath = model.path.empty() ? 
                            (executablePath / model.name).string() : model.path;
                        std::string command = "python \"" + scriptPath.string() + 
                            "\" \"" + modelPath + "\" " + std::to_string(model.port);
                        std::cout << "Executing command: " << command << std::endl;
                        std::system(command.c_str());
                    } });
                        }
                    }

                    // Wait for prediction scripts to start
                    std::this_thread::sleep_for(std::chrono::seconds(2));

                    // Initialize model sockets
                    if (!initPredictionSocket())
                    {
                        std::cerr << "Failed to initialize prediction sockets" << std::endl;
                        wiresharkRunning = false;
                        simulationRunning = false;
                    }

                    // Start wireshark capture
                    wiresharkThread = std::thread([&]()
                                                  {
            try {
                startWiresharkCapture();
            }
            catch (const std::exception& e) {
                std::cerr << "Exception in Wireshark thread: " << e.what() << std::endl;
            } });
                }
            }
            else
            {
                if (ImGui::Button("Stop Capture"))
                {
                    stopWiresharkCapture();
                    simulationRunning = false;
                }
            }
        }

        // Simulation Results (keep existing code)
        if (simulationEnded || (stopSimulationRequested && !simulationRunning))
        {
            ImGui::Text("Simulation Ended");

            if (ImGui::Button("Save Results"))
            {
                for (const auto &stats : modelStats)
                {
                    auto it = std::find_if(availableModels.begin(), availableModels.end(),
                                           [&stats](const ModelInfo &model)
                                           {
                                               return model.name == stats["model_name"];
                                           });
                    if (it != availableModels.end())
                    {
                        saveModelAndStatistics(*it, stats);
                    }
                }
                ImGui::OpenPopup("Save Confirmation");
            }

            if (ImGui::BeginPopupModal("Save Confirmation", NULL, ImGuiWindowFlags_AlwaysAutoResize))
            {
                ImGui::Text("Results saved successfully");
                if (ImGui::Button("OK", ImVec2(120, 0)))
                {
                    ImGui::CloseCurrentPopup();
                }
                ImGui::EndPopup();
            }

            if (ImGui::BeginTable("Model Statistics", 7, ImGuiTableFlags_Borders | ImGuiTableFlags_RowBg))
            {
                // Set up the table headers
                ImGui::TableSetupColumn("Model Name");
                ImGui::TableSetupColumn("Total Predictions");
                ImGui::TableSetupColumn("Accuracy");
                ImGui::TableSetupColumn("Precision");
                ImGui::TableSetupColumn("Recall");
                ImGui::TableSetupColumn("F1 Score");
                ImGui::TableSetupColumn("Avg Time (ms)");
                ImGui::TableHeadersRow();

                // Add rows for each model
                for (const auto &stats : modelStats)
                {
                    ImGui::TableNextRow();

                    ImGui::TableSetColumnIndex(0);
                    ImGui::Text("%s", stats["model_name"].get<std::string>().c_str());

                    ImGui::TableSetColumnIndex(1);
                    ImGui::Text("%d", stats["total_predictions"].get<int>());

                    ImGui::TableSetColumnIndex(2);
                    ImGui::Text("%.4f", stats["accuracy"].get<double>());

                    ImGui::TableSetColumnIndex(3);
                    ImGui::Text("%.4f", stats["precision"].get<double>());

                    ImGui::TableSetColumnIndex(4);
                    ImGui::Text("%.4f", stats["recall"].get<double>());

                    ImGui::TableSetColumnIndex(5);
                    ImGui::Text("%.4f", stats["f1_score"].get<double>());

                    ImGui::TableSetColumnIndex(6);
                    ImGui::Text("%.3f", stats["avg_prediction_time"].get<double>());
                }
                ImGui::EndTable();
            }

            // Display attack-specific metrics in a separate table
            if (!modelStats.empty())
            {
                ImGui::Spacing();
                ImGui::Text("Attack-Specific Metrics");

                if (ImGui::BeginTable("Attack Metrics", 5, ImGuiTableFlags_Borders | ImGuiTableFlags_RowBg))
                {
                    // Set up the table headers
                    ImGui::TableSetupColumn("Model Name");
                    ImGui::TableSetupColumn("Attack Type");
                    ImGui::TableSetupColumn("Precision");
                    ImGui::TableSetupColumn("Recall");
                    ImGui::TableSetupColumn("F1 Score");
                    ImGui::TableHeadersRow();

                    // Add rows for each model and attack type
                    for (const auto &stats : modelStats)
                    {
                        const auto &attack_metrics = stats["attack_metrics"];
                        std::string model_name = stats["model_name"].get<std::string>();

                        for (const auto &[attack_type, metrics] : attack_metrics.items())
                        {
                            ImGui::TableNextRow();

                            ImGui::TableSetColumnIndex(0);
                            ImGui::Text("%s", model_name.c_str());

                            ImGui::TableSetColumnIndex(1);
                            // Capitalize first letter of attack type
                            std::string display_attack = attack_type;
                            if (!display_attack.empty())
                                display_attack[0] = std::toupper(display_attack[0]);
                            ImGui::Text("%s", display_attack.c_str());

                            ImGui::TableSetColumnIndex(2);
                            ImGui::Text("%.4f", metrics["precision"].get<double>());

                            ImGui::TableSetColumnIndex(3);
                            ImGui::Text("%.4f", metrics["recall"].get<double>());

                            ImGui::TableSetColumnIndex(4);
                            ImGui::Text("%.4f", metrics["f1_score"].get<double>());
                        }
                    }
                    ImGui::EndTable();
                }
            }
        }
        // Plot Controls and Rendering
        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Text("Metrics Display:");
        ImGui::Columns(2, "MetricsColumns");
        for (size_t i = 0; i < metricLabels.size(); ++i)
        {
            bool isVisible = plotVisibility[i];
            if (ImGui::Checkbox(metricLabels[i].c_str(), &isVisible))
            {
                plotVisibility[i] = isVisible;
            }
            if (i % 2 == 1)
                ImGui::NextColumn();
        }
        ImGui::Columns(1);

        if (simulationRunning)
        {
            processData();
        }

        renderPlots();
        renderModelPlots();

        ImGui::End();

        // Rendering
        ImGui::Render();
        int display_w, display_h;
        glfwGetFramebufferSize(window, &display_w, &display_h);
        glViewport(0, 0, display_w, display_h);
        glClear(GL_COLOR_BUFFER_BIT);
        ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
        glfwSwapBuffers(window);
    }

    // Cleanup
    std::cout << "Starting cleanup..." << std::endl;

    shouldExit = true;
    applicationClosing = true;
    simulationRunning = false;
    receiverRunning = false;
    stopSimulationRequested = true;

    if (!simulationEnded)
    {
        std::cout << "Stopping simulation..." << std::endl;
        if (currentDataSource == DataSource::SIMULATION)
        {
            stopSimulation();
        }
        else
        {
            stopWiresharkCapture();
        }
    }

    std::cout << "Terminating Python processes..." << std::endl;
    terminatePythonProcesses();

    std::cout << "Closing model sockets..." << std::endl;
    for (auto &model : availableModels)
    {
        if (model.socket != INVALID_SOCKET)
        {
            shutdown(model.socket, SD_BOTH);
            closesocket(model.socket);
            model.socket = INVALID_SOCKET;
        }
    }

    std::cout << "Waiting for Python threads..." << std::endl;
    for (auto &thread : pythonScriptThreads)
    {
        if (thread.joinable())
        {
            std::thread timeoutThread([&thread]()
                                      { thread.join(); });
            auto start = std::chrono::steady_clock::now();
            while (timeoutThread.joinable())
            {
                if (std::chrono::steady_clock::now() - start > std::chrono::seconds(3))
                {
                    std::cout << "Thread join timed out" << std::endl;
                    break;
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
        }
    }
    pythonScriptThreads.clear();

    if (wiresharkThread.joinable())
    {
        wiresharkThread.join();
    }

    std::cout << "Closing listen socket..." << std::endl;
    if (listenSocket != INVALID_SOCKET)
    {
        shutdown(listenSocket, SD_BOTH);
        closesocket(listenSocket);
        listenSocket = INVALID_SOCKET;
    }

    std::cout << "Waiting for receiver thread..." << std::endl;
    if (receiverThread.joinable())
    {
        std::thread timeoutThread([&receiverThread]()
                                  { receiverThread.join(); });
        auto start = std::chrono::steady_clock::now();
        while (timeoutThread.joinable())
        {
            if (std::chrono::steady_clock::now() - start > std::chrono::seconds(3))
            {
                std::cout << "Receiver thread join timed out" << std::endl;
                break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

    std::cout << "Performing final cleanup..." << std::endl;
    WSACleanup();
    Py_Finalize();

    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplGlfw_Shutdown();
    ImGui::DestroyContext();
    ImPlot::DestroyContext();

    glfwDestroyWindow(window);
    glfwTerminate();

    std::cout << "Cleanup complete." << std::endl;
    return 0;
}