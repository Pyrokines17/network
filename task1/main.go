package main

import (
	"fmt"
	"log"
	"net"
	"os"
	"strings"
	"sync"
	"time"
)

const (
	message     = "ping"
	timeout     = 5 * time.Second
	checkPeriod = 1 * time.Second
)

var (
	mu        sync.Mutex
	instances = make(map[string]time.Time)
)

func isIPv4(addr string) bool {
	return net.ParseIP(addr).To4() != nil
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run main.go <multicast_group> <interface>")
		os.Exit(1)
	}

	interfaceName := "wlo1"

	if len(os.Args) > 2 {
		interfaceName = os.Args[2]
	}

	multicastAddr := os.Args[1]
	addr, err := net.ResolveUDPAddr("udp", multicastAddr)

	if err != nil {
		log.Fatalf("Failed to resolve address: %v", err)
	}

	var iface *net.Interface

	if !isIPv4(addr.IP.String()) {
		iface, err = net.InterfaceByName(interfaceName)

		if err != nil {
			log.Fatalf("Failed to get network interface: %v", err)
		}
	}

	conn, err := net.ListenMulticastUDP("udp", iface, addr)

	if err != nil {
		log.Fatalf("Failed to listen on address: %v", err)
	}

	defer func(conn *net.UDPConn) {
		err := conn.Close()

		if err != nil {
			fmt.Printf("Failed to close connection: %v\n", err)
		}
	}(conn)

	err = conn.SetReadBuffer(4096)

	if err != nil {
		log.Fatalf("Failed to set read buffer: %v", err)
	}

	go sendPresence(addr, iface)
	go listenForCopies(conn)

	monitorInstances()
}

func sendPresence(addr *net.UDPAddr, iface *net.Interface) {
	var conn *net.UDPConn
	var err error

	if iface != nil {
		conn, err = net.ListenUDP("udp6", &net.UDPAddr{IP: net.IPv6unspecified, Zone: iface.Name})
	} else {
		conn, err = net.ListenUDP("udp4", nil)
	}

	if err != nil {
		log.Printf("Failed to dial address: %v", err)
	}

	defer func(conn *net.UDPConn) {
		err := conn.Close()

		if err != nil {
			log.Printf("Failed to close connection: %v", err)
		}
	}(conn)

	for {
		_, err := conn.WriteToUDP([]byte(message), addr)

		if err != nil {
			log.Printf("Failed to write to connection: %v", err)
		}

		time.Sleep(checkPeriod)
	}
}

func listenForCopies(conn *net.UDPConn) {
	buffer := make([]byte, 1024)

	for {
		n, src, err := conn.ReadFromUDP(buffer)

		if err != nil {
			log.Printf("Failed to read from connection: %v", err)
		}

		if strings.TrimSpace(string(buffer[:n])) == message {
			mu.Lock()
			_, exists := instances[src.String()]
			instances[src.String()] = time.Now()
			mu.Unlock()

			if !exists {
				fmt.Println("New instance detected")
				printInstances()
			}
		}
	}
}

func monitorInstances() {
	for {
		time.Sleep(checkPeriod)

		mu.Lock()
		now := time.Now()
		updated := false

		for ip, lastSeen := range instances {
			if now.Sub(lastSeen) > timeout {
				delete(instances, ip)
				updated = true
			}
		}

		mu.Unlock()

		if updated {
			fmt.Println("Instance removed")
			printInstances()
		}
	}
}

func printInstances() {
	mu.Lock()
	defer mu.Unlock()

	fmt.Println("Alive instances:")

	for ip := range instances {
		fmt.Println(ip)
	}

	fmt.Println()
}
